from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
import logging
from .services import create_notification
from .tasks import send_notification_task

logger = logging.getLogger(__name__)


def schedule_cart_reminder(user):
    """
    Schedule a task to create and send a cart reminder notification 1 hour later.
    """
    # FIX: Do not create the notification record here.
    # Passing user info to a task that handles creation AFTER the delay
    # prevents the notification from appearing in the UI dropdown immediately.
    send_notification_task.apply_async(
        args=[user.id, "cart_reminder"], countdown=3600  # 1 hour in seconds
    )


def send_status_change_notification(user, order_item, status_label, is_return=False):
    """
    Sends unified notifications (In-App & Email) for order item status changes or return request updates.
    """
    try:
        product_name = order_item.variant.product.name
        order_number = order_item.order.order_number

        if is_return:
            title = f"Return Request {status_label}"
            if status_label == "Approved":
                message_body = f"Your return request for '{product_name}' in order {order_number} has been APPROVED."
            else:
                message_body = f"Your return request for '{product_name}' in order {order_number} has been REJECTED."
            redirect_url = reverse("user_orders")
        else:
            title = f"Order Item {status_label.title()}"
            message_body = f"The status of your item '{product_name}' in order {order_number} has been updated to {status_label}."
            redirect_url = reverse("user_orders")

        # 1. In-App Notification
        create_notification(
            user=user,
            type=f"order_{status_label.lower().replace(' ', '_')}",
            title=title,
            message=message_body,
            redirect_url=redirect_url,
        )

        # 2. Email Notification
        send_mail(
            subject=f"{title} - {order_number}",
            message=f"""Hi {user.first_name},

{message_body}

Thank you for shopping with EasyBuy!""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Unified Notification Failed ({status_label}): {str(e)}")
