from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import invalidate_user_common_cache, invalidate_user_header_cache
from .models import Cart, NotificationPreference, Wishlist
from .models import CartItem, WishlistItem


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_default_user_records(sender, instance, created, **kwargs):
    if not created:
        return

    Cart.objects.get_or_create(user=instance)
    NotificationPreference.objects.get_or_create(user=instance)
    Wishlist.objects.get_or_create(user=instance, wishlist_name="My Wishlist")


@receiver(post_save, sender=CartItem)
@receiver(post_delete, sender=CartItem)
def invalidate_cart_header_cache(sender, instance, **kwargs):
    user_id = getattr(instance.cart, "user_id", None)
    invalidate_user_header_cache(user_id)


@receiver(post_save, sender=Wishlist)
@receiver(post_delete, sender=Wishlist)
def invalidate_wishlist_common_cache(sender, instance, **kwargs):
    invalidate_user_common_cache(instance.user_id)


@receiver(post_save, sender=WishlistItem)
@receiver(post_delete, sender=WishlistItem)
def invalidate_wishlist_item_common_cache(sender, instance, **kwargs):
    wishlist = getattr(instance, "wishlist", None)
    user_id = getattr(wishlist, "user_id", None)
    if user_id is None and instance.wishlist_id:
        user_id = (
            Wishlist.objects.filter(id=instance.wishlist_id)
            .values_list("user_id", flat=True)
            .first()
        )
    invalidate_user_common_cache(user_id)
