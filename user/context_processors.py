from core.models import Notification
from user.models import CartItem, WishlistItem


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
        cart_count = CartItem.objects.filter(cart__user=request.user).count()
        wishlist_count = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()

        return {
            "unread_notification_count": unread_count,
            "recent_notifications": recent_notifications,
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
        }
    return {
        "unread_notification_count": 0,
        "recent_notifications": [],
        "cart_count": 0,
        "wishlist_count": 0,
    }

