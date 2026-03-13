from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
import random
import string
from .models import Category, User, Otp


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


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
        print(f"Error sending email: {e}")
        return False


def all_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            role = user.role
            if role == "CUSTOMER":
                return redirect("home")
            elif role == "ADMIN":
                return redirect("admin_dashboard")
            elif role == "SELLER":
                return redirect("seller_dashboard")
        else:
            return render(
                request, "core/login.html", {"error": "Invalid username or password"}
            )
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
    return render(request, "core/login.html", {"message": "Logged out successfully!"})
