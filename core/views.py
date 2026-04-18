from datetime import timedelta
import logging
import random
import string

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from seller.models import ProductVariant

from .cache_utils import get_cached_google_login_enabled
from .forms import EasyBuyPasswordChangeForm, EasyBuySetPasswordForm, ForgotPasswordForm
from .models import Category, NotificationConfig, NotificationDelivery, Otp, StockNotification, User
from .services import create_notification
from .utils import build_public_absolute_uri


logger = logging.getLogger(__name__)
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60
OTP_ATTEMPT_LIMIT = 5
OTP_ATTEMPT_WINDOW_SECONDS = 10 * 60


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


def _login_context():
    return {"google_login_enabled": get_cached_google_login_enabled()}


def _normalize_registration_payload(request):
    return {
        "username": (request.POST.get("username") or "").strip(),
        "email": (request.POST.get("email") or "").strip().lower(),
        "phone_number": (request.POST.get("phone_number") or "").strip(),
        "password1": request.POST.get("password1") or "",
        "password2": request.POST.get("password2") or "",
    }


def _get_pending_customer_by_email(email):
    if not email:
        return None
    return (
        User.objects.filter(email__iexact=email, role="CUSTOMER", is_active=False)
        .order_by("id")
        .first()
    )


def _client_ip(request):
    return (request.META.get("REMOTE_ADDR") or "unknown").strip()


def _rate_limit_cache_key(prefix, request, identifier):
    safe_identifier = str(identifier or "anonymous").strip().lower() or "anonymous"
    return f"security:{prefix}:{_client_ip(request)}:{safe_identifier}"


def _rate_limit_reached(prefix, request, identifier, limit):
    key = _rate_limit_cache_key(prefix, request, identifier)
    return int(cache.get(key, 0) or 0) >= limit


def _record_rate_limited_failure(prefix, request, identifier, ttl_seconds):
    key = _rate_limit_cache_key(prefix, request, identifier)
    attempts = int(cache.get(key, 0) or 0) + 1
    cache.set(key, attempts, ttl_seconds)
    return attempts


def _clear_rate_limit(prefix, request, identifier):
    cache.delete(_rate_limit_cache_key(prefix, request, identifier))


def _account_home_url(user):
    if not getattr(user, "is_authenticated", False):
        return reverse("home")
    if user.role == "ADMIN":
        return reverse("admin_dashboard")
    if user.role == "SELLER":
        seller_profile = getattr(user, "seller_profile", None)
        if seller_profile and seller_profile.status == "APPROVED":
            return reverse("seller_dashboard")
        return reverse("seller_waiting")
    return reverse("profile_settings")


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


def send_password_reset_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = build_public_absolute_uri(
        request,
        reverse("reset_password", kwargs={"uidb64": uid, "token": token})
    )
    subject = "Reset Your EasyBuy Password"
    message = f"""
    Hello {user.username},

    We received a request to reset your EasyBuy password.
    Open this link to choose a new password:
    {reset_url}

    If you did not request a password reset, you can ignore this email.

    EasyBuy Team
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error("Error sending password reset email: %s", exc)
        return False


def all_login(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password")
        if _rate_limit_reached(
            "login", request, username, LOGIN_ATTEMPT_LIMIT
        ):
            messages.error(
                request,
                "Too many login attempts. Please wait 15 minutes and try again.",
            )
            return render(request, "core/login.html", _login_context())

        user = authenticate(request, username=username, password=password)
        if user is not None:
            _clear_rate_limit("login", request, username)
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
                seller_profile = getattr(user, "seller_profile", None)
                if seller_profile and seller_profile.status == "APPROVED":
                    return redirect("seller_dashboard")
                return redirect("seller_waiting")
        else:
            attempts = _record_rate_limited_failure(
                "login",
                request,
                username,
                LOGIN_ATTEMPT_WINDOW_SECONDS,
            )
            if attempts >= LOGIN_ATTEMPT_LIMIT:
                messages.error(
                    request,
                    "Too many login attempts. Please wait 15 minutes and try again.",
                )
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
                    user = _get_pending_customer_by_email(email)
                    if user is None:
                        raise User.DoesNotExist
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

        payload = _normalize_registration_payload(request)
        username = payload["username"]
        email = payload["email"]
        phone_number = payload["phone_number"]
        password1 = payload["password1"]
        password2 = payload["password2"]

        if not username or not email or not password1:
            messages.error(request, "All fields are required.")
            return redirect("register")
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")
        existing_user = _get_pending_customer_by_email(email)
        active_email_conflict = (
            User.objects.filter(email__iexact=email).exclude(pk=getattr(existing_user, "pk", None)).exists()
        )
        username_conflict = User.objects.filter(username__iexact=username)
        if existing_user:
            username_conflict = username_conflict.exclude(pk=existing_user.pk)
        phone_conflict = User.objects.filter(phone_number=phone_number) if phone_number else User.objects.none()
        if existing_user:
            phone_conflict = phone_conflict.exclude(pk=existing_user.pk)

        if username_conflict.exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        if active_email_conflict:
            messages.error(request, "Email already registered.")
            return redirect("register")
        if phone_conflict.exists():
            messages.error(request, "Phone number already registered.")
            return redirect("register")

        otp_code = generate_otp()
        try:
            with transaction.atomic():
                user = existing_user or User(email=email, role="CUSTOMER")
                user.username = username
                user.email = email
                user.phone_number = phone_number or None
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
            "phone_number": phone_number,
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
    email = (request.POST.get("email") or "").strip().lower()
    otp_input = (request.POST.get("otp") or "").strip()

    if not email or not otp_input:
        messages.error(request, "Email and OTP are required.")
        return redirect("register")

    if _rate_limit_reached("otp", request, email, OTP_ATTEMPT_LIMIT):
        messages.error(
            request,
            "Too many OTP attempts. Please request a new OTP and try again later.",
        )
        return render(request, "core/verify_otp.html", {"email": email})

    try:
        user = User.objects.get(email__iexact=email)
        otp_record = Otp.objects.filter(user=user, verified=False).latest("created_at")

        if timezone.now() - otp_record.created_at > timedelta(minutes=5):
            messages.error(request, "OTP has expired. Please request a new one.")
            return render(request, "core/verify_otp.html", {"email": email})

        if not otp_record.matches(otp_input):
            attempts = _record_rate_limited_failure(
                "otp",
                request,
                email,
                OTP_ATTEMPT_WINDOW_SECONDS,
            )
            if attempts >= OTP_ATTEMPT_LIMIT:
                messages.error(
                    request,
                    "Too many OTP attempts. Please request a new OTP and try again later.",
                )
            else:
                messages.error(request, "Invalid OTP. Please try again.")
            return render(request, "core/verify_otp.html", {"email": email})

        otp_record.verified = True
        otp_record.save()

        user.is_active = True
        user.save()
        _clear_rate_limit("otp", request, email)

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
        _record_rate_limited_failure(
            "otp", request, email, OTP_ATTEMPT_WINDOW_SECONDS
        )
        messages.error(request, "Invalid email address.")
    except Otp.DoesNotExist:
        _record_rate_limited_failure(
            "otp", request, email, OTP_ATTEMPT_WINDOW_SECONDS
        )
        messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "core/verify_otp.html", {"email": email})


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        user = (
            User.objects.filter(email__iexact=email, is_active=True)
            .order_by("id")
            .first()
        )

        if user and not send_password_reset_email(request, user):
            messages.error(
                request,
                "We could not send the reset email right now. Please try again.",
            )
        else:
            messages.success(
                request,
                "If that email is registered, a password reset link has been sent.",
            )
            form = ForgotPasswordForm()

    return render(request, "core/forgot_password.html", {"form": form})


def reset_password_view(request, uidb64, token):
    user = None
    validlink = False

    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True

    form = EasyBuySetPasswordForm(user, request.POST or None) if validlink else None

    if request.method == "POST" and validlink and form.is_valid():
        form.save()
        messages.success(
            request, "Your password has been reset. Please sign in with the new password."
        )
        return redirect("all_login")

    return render(
        request,
        "core/reset_password.html",
        {"form": form, "validlink": validlink},
    )


@login_required
def change_password_view(request):
    form = EasyBuyPasswordChangeForm(request.user, request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed successfully.")
        return redirect("change_password")

    return render(
        request,
        "core/change_password.html",
        {"form": form, "account_home_url": _account_home_url(request.user)},
    )


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

def discover_view(request):
    return render(request, "core/discover.html")


def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "db": db_ok}, status=status)
