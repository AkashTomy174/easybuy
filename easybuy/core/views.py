from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
import random
import string
import logging
from .models import Category, User, Otp, AdSpace, AdBooking
from celery import shared_task
from django.utils import timezone
from .models import Notification, NotificationDelivery, NotificationConfig
from .forms import AdBookingForm
from django.db.models import Q
from django.http import JsonResponse
from .models import StockNotification
from easybuy.seller.models import ProductVariant
from .services import create_notification


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


logger = logging.getLogger(__name__)


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
            elif role == "ADMIN":
                return redirect("admin_dashboard")
            elif role == "SELLER":
                return redirect("seller_dashboard")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "core/login.html")

    return render(request, "core/login.html")


def register_view(request):
    if request.method == "POST":
        if "otp" in request.POST and request.POST.get("otp"):
            return verify_otp(request)

        if "resend" in request.POST:
            email = request.POST.get("email")
            if email:
                otp_code = generate_otp()

                Otp.objects.filter(user__email=email).delete()

                try:
                    user = User.objects.get(email=email)
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
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        if "pending_registration" in request.session:
            pending = request.session["pending_registration"]
            pending["username"] = username
            pending["email"] = email
            pending["password"] = password1
            request.session["pending_registration"] = pending
        else:
            request.session["pending_registration"] = {
                "username": username,
                "email": email,
                "password": password1,
            }

        otp_code = generate_otp()

        Otp.objects.filter(user__email=email).delete()

        user, created = User.objects.get_or_create(
            email=email, defaults={"username": username, "is_active": False}
        )

        if not created:
            user.username = username
            user.set_password(password1)
            user.is_active = False
            user.save()

        Otp.objects.create(user=user, otp=otp_code)

        if send_otp_email(email, otp_code):
            messages.success(request, f"OTP sent to {email}. Please verify.")
            return render(request, "core/verify_otp.html", {"email": email})
        else:
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
        otp_record = Otp.objects.filter(
            user=user, otp=otp_input, verified=False
        ).latest("created_at")

        if timezone.now() - otp_record.created_at > timedelta(minutes=5):
            messages.error(request, "OTP has expired. Please request a new one.")
            return render(request, "core/verify_otp.html", {"email": email})

        otp_record.verified = True
        otp_record.save()

        user.is_active = True

        pending = request.session.get("pending_registration")
        if pending and pending.get("email") == email:
            user.set_password(pending["password"])

        user.save()

        if "pending_registration" in request.session:
            del request.session["pending_registration"]

        login(request, user)
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


# notifcation related things

from .services import create_notification


def place_order_view(request):
    user = request.user
    # ... your order creation logic ...
    create_notification(
        user=user,
        type="order_success",
        title="Order Placed!",
        message="Your order has been successfully placed.",
    )
    # return response immediately


@login_required
def ad_space_list(request):
    spaces = AdSpace.objects.filter(is_active=True)

    # Fetch active ads for sidebars
    today = timezone.now().date()

    # Show ACTIVE ads to everyone, plus YOUR own ads (Pending/Active) for preview
    filter_query = Q(status="ACTIVE", start_date__lte=today, end_date__gte=today)
    if request.user.is_authenticated:
        filter_query |= Q(user=request.user, end_date__gte=today)

    active_ads = (
        AdBooking.objects.filter(filter_query)
        .select_related("ad_space")
        .distinct()
        .order_by("-created_at")
    )

    left_ad = active_ads.filter(ad_space__name__icontains="left").first()
    if not left_ad:
        left_ad = active_ads.first()

    right_ad = active_ads.filter(ad_space__name__icontains="right").first()
    if not right_ad:
        if left_ad:
            right_ad = active_ads.exclude(id=left_ad.id).first()
        else:
            right_ad = active_ads.last()

    return render(
        request,
        "core/ad_space_list.html",
        {"spaces": spaces, "left_ad": left_ad, "right_ad": right_ad},
    )


@login_required
def book_ad(request, space_id):
    space = get_object_or_404(AdSpace, id=space_id, is_active=True)

    if request.method == "POST":
        form = AdBookingForm(request.POST, request.FILES)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.ad_space = space
            # Trigger calculation in save method
            booking.save()
            messages.success(
                request,
                f"Ad booking request submitted for {space.name}. Total cost: ₹{booking.total_cost}",
            )
            return redirect("ad_space_list")
    else:
        form = AdBookingForm()

    return render(request, "core/book_ad.html", {"form": form, "space": space})


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
