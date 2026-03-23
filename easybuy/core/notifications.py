from datetime import timedelta
from django.utils import timezone
from .services import create_notification
from .tasks import send_notification_task


def schedule_cart_reminder(user):
    """
    Create a cart reminder notification and schedule it to be sent 1 hour later.
    """
    # 1. Create the notification
    notification = create_notification(
        user=user,
        type="cart_reminder",
        title="You left items in your cart!",
        message="Complete your purchase before your items go out of stock.",
    )

    # 2. Schedule Celery task to send it after 1 hour
    send_notification_task.apply_async(
        args=[notification.id], eta=timezone.now() + timedelta(hours=1)
    )
