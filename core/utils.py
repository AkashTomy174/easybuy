from django.conf import settings
from django.core.mail import send_mail
from urllib.parse import urljoin

from .whatsapp_utils import whatsapp_notifier


def send_whatsapp(phone_number, message):
    """
    Integrate with your WhatsApp API provider.
    """
    if not phone_number:
        raise ValueError("Phone number is required")

    if not whatsapp_notifier.send_message(phone_number, message):
        raise RuntimeError("WhatsApp delivery failed")


def send_email(email, subject, message):
    """
    Integrate with your email provider (SMTP, SendGrid, etc.).
    """
    if not email:
        raise ValueError("Email address is required")

    sent_count = send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    if sent_count != 1:
        raise RuntimeError("Email delivery failed")


def build_public_absolute_uri(request, location):
    location = str(location or "/")
    if location.startswith(("http://", "https://")):
        return location

    public_base_url = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    if public_base_url:
        return urljoin(f"{public_base_url}/", location.lstrip("/"))

    return request.build_absolute_uri(location)
