from .models import Notification
from .tasks import send_notification_task


def create_notification(user, type, title, message, image_url=None, redirect_url=None):
    """
    Create a notification and trigger background delivery via Celery.
    """
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        image_url=image_url,
        redirect_url=redirect_url,
    )
    send_notification_task.delay(notification.id)
    return notification


from easybuy.core.models import StockNotification


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

        image_url = (
            variant.product_images.first().image.url
            if variant.product_images.first()
            else None
        )
        product_url = f"/product/{variant.product.slug}/"

        create_notification(
            user=notif.user,
            type="stock_available",
            title="🔔 Back in Stock!",
            message=f"Your watched item '{variant.product.name}' is now available again!",
            image_url=image_url,
            redirect_url=product_url,
        )
