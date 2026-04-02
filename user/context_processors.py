from core.models import Notification


def notifications(request):
    """
    Context processor to make notifications available in all templates.
    """
    if request.user.is_authenticated:
        # Get unread count
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        # Get recent 5 notifications for the dropdown
        recent_notifications = Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:5]

        return {
            "unread_notification_count": unread_count,
            "recent_notifications": recent_notifications,
        }
    return {"unread_notification_count": 0, "recent_notifications": []}

