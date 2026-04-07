from datetime import timedelta
import logging
import random
import string

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from seller.models import ProductVariant

from .models import Category, NotificationConfig, NotificationDelivery, Otp, StockNotification, User
from .services import create_notification


logger = logging.getLogger(__name__)


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


def _login_context():
    google_login_enabled = False
    try:
        from allauth.socialaccount.models import SocialApp

        google_login_enabled = SocialApp.objects.filter(provider="google").exists()
    except Exception:
        google_login_enabled = False

    return {"google_login_enabled": google_login_enabled}


def send_otp_email(email, otp):
    subject = "Verify Your EasyBuy Account"
    message = f"""
    Welcome to EasyBuy!
    Your verification code is: {otp}
    This code will expire in 10 minutes.
    If you didn't create this account, please ignore this email.
    Best regards,
    EasyBuy Team
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def all_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if request.POST.get("remember"):
                request.session["remember_me"] = True
            else:
                request.session["remember_me"] = False
            messages.success(request, "Welcome back!")
            role = user.role
            if role == "CUSTOMER":
                return redirect("home")
            if role == "ADMIN":
                return redirect("admin_dashboard")
            if role == "SELLER":
                return redirect("seller_dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "core/login.html", _login_context())

    return render(request, "core/login.html", _login_context())


def register_view(request):
    if request.method == "POST":
        if "otp" in request.POST and request.POST.get("otp"):
            return verify_otp(request)

        if "resend" in request.POST:
            email = request.POST.get("email") or request.session.get(
                "pending_registration", {}
            ).get("email")
            if email:
                otp_code = generate_otp()
                try:
                    user = User.objects.get(email=email)
                    Otp.objects.filter(user=user).delete()
                    Otp.objects.create(user=user, otp=otp_code)

                    if send_otp_email(email, otp_code):
                        messages.success(
                            request,
                            f"New OTP sent to {email}. Please check your inbox.",
                        )
                    else:
                        messages.error(request, "Failed to send OTP. Please try again.")
                except User.DoesNotExist:
                    messages.error(request, "User not found.")

                return render(request, "core/verify_otp.html", {"email": email})

        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if not username or not email or not password1:
            messages.error(request, "All fields are required.")
            return redirect("register")
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")
        existing_user = User.objects.filter(email=email).first()
        username_conflict = User.objects.filter(username=username)
        if existing_user:
            username_conflict = username_conflict.exclude(pk=existing_user.pk)

        if username_conflict.exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        if existing_user and existing_user.is_active:
            messages.error(request, "Email already registered.")
            return redirect("register")

        otp_code = generate_otp()
        try:
            with transaction.atomic():
                user = existing_user or User(email=email, role="CUSTOMER")
                user.username = username
                user.role = "CUSTOMER"
                user.is_active = False
                user.set_password(password1)
                user.save()

                Otp.objects.filter(user=user).delete()
                Otp.objects.create(user=user, otp=otp_code)
        except Exception as exc:
            logger.error("Registration setup failed: %s", exc)
            messages.error(request, "Unable to start registration. Please try again.")
            return redirect("register")

        request.session["pending_registration"] = {
            "username": username,
            "email": email,
        }

        if send_otp_email(email, otp_code):
            messages.success(request, f"OTP sent to {email}. Please verify.")
            return render(request, "core/verify_otp.html", {"email": email})

        messages.error(request, "Failed to send OTP. Please try again.")
        return redirect("register")

    if "pending_registration" in request.session:
        del request.session["pending_registration"]

    return render(request, "core/register.html")


def verify_otp(request):
    email = request.POST.get("email")
    otp_input = request.POST.get("otp")

    if not email or not otp_input:
        messages.error(request, "Email and OTP are required.")
        return redirect("register")

    try:
        user = User.objects.get(email=email)
        otp_record = Otp.objects.filter(user=user, verified=False).latest("created_at")

        if timezone.now() - otp_record.created_at > timedelta(minutes=5):
            messages.error(request, "OTP has expired. Please request a new one.")
            return render(request, "core/verify_otp.html", {"email": email})

        if not otp_record.matches(otp_input):
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, "core/verify_otp.html", {"email": email})

        otp_record.verified = True
        otp_record.save()

        user.is_active = True
        user.save()

        from user.models import Cart, NotificationPreference, Wishlist

        Cart.objects.get_or_create(user=user)
        NotificationPreference.objects.get_or_create(user=user)
        Wishlist.objects.get_or_create(user=user, wishlist_name="My Wishlist")

        if "pending_registration" in request.session:
            del request.session["pending_registration"]

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Account verified successfully!")
        return redirect("home")

    except User.DoesNotExist:
        messages.error(request, "Invalid email address.")
    except Otp.DoesNotExist:
        messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "core/verify_otp.html", {"email": email})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("home")


def place_order_view(request):
    user = request.user
    create_notification(
        user=user,
        type="order_success",
        title="Order Placed!",
        message="Your order has been successfully placed.",
    )


@login_required
def toggle_stock_notification(request, variant_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"})

    variant = get_object_or_404(ProductVariant, id=variant_id)
    notification, created = StockNotification.objects.get_or_create(
        user=request.user,
        variant=variant,
        defaults={
            "email": request.user.email,
            "phone": getattr(request.user, "phone_number", ""),
        },
    )

    if not created:
        notification.delete()
        is_notified = False
        msg = "Stock notification turned off"
    else:
        is_notified = True
        msg = "You will be notified when back in stock!"

    return JsonResponse({"success": True, "notified": is_notified, "message": msg})


def contact_view(request):
    return render(request, "core/contact.html")


def returns_view(request):
    return render(request, "core/returns.html")


def track_order_view(request):
    return render(request, "core/track_order.html")
