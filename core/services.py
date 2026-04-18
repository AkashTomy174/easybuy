import logging
from .models import Notification, StockNotification

logger = logging.getLogger(__name__)


def create_notification(user, type, title, message, image_url=None, redirect_url=None):
    """
    Create a notification and trigger background delivery via Celery.
    """
    from .tasks import send_notification_task

    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        image_url=image_url,
        redirect_url=redirect_url,
    )
    try:
        send_notification_task.delay(notification.id)
    except Exception as e:
        logger.warning(f"Celery unavailable, notification {notification.id} saved to DB only: {e}")
    return notification

def check_stock_notifications(variant):
    """
    Check for pending stock notifications and send them when stock becomes available.
    """
    notifications = StockNotification.objects.filter(
        variant=variant, notified=False
    ).select_related("user")

    for notif in notifications:
        notif.notified = True
        notif.save()

        primary_image = variant.images.filter(is_primary=True).first() or variant.images.first()
        image_url = primary_image.image.url if primary_image and primary_image.image else None
        product_url = f"/product/{variant.product.slug}/"

        create_notification(
            user=notif.user,
            type="stock_available",
            title="🔔 Back in Stock!",
            message=f"Your watched item '{variant.product.name}' is now available again!",
            image_url=image_url,
            redirect_url=product_url,
        )
