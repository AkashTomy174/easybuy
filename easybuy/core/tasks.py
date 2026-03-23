import logging
from celery import shared_task
from django.utils import timezone
from .models import Notification, NotificationDelivery, NotificationConfig
from .utils import send_whatsapp, send_email

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(self, notification_id):
    """
    Send notifications for all enabled channels asynchronously.
    Retries on failure up to 3 times.
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        config = NotificationConfig.objects.get(type=notification.type)
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return
    except NotificationConfig.DoesNotExist:
        logger.warning(f"No config found for type {notification.type}")
        return

    channels = []
    if config.enable_whatsapp:
        channels.append("whatsapp")
    if config.enable_email:
        channels.append("email")
    if config.enable_in_app:
        channels.append("in_app")

    for channel in channels:
        delivery, _ = NotificationDelivery.objects.get_or_create(
            notification=notification, channel=channel
        )
        try:
            if channel == "whatsapp":
                send_whatsapp(notification.user.phone, notification.message)
            elif channel == "email":
                send_email(notification.user.email, notification.title, notification.message)
            elif channel == "in_app":
                # In-app is usually instant
                pass
            delivery.status = "sent"
        except Exception as e:
            delivery.status = "failed"
            logger.error(f"Failed to send {channel} for notification {notification_id}: {e}")
        finally:
            delivery.sent_at = timezone.now()
            delivery.save()