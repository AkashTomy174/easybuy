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
        redirect_url=redirect_url
    )
    send_notification_task.delay(notification.id)
    return notification