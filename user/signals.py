from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cart, NotificationPreference, Wishlist


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_default_user_records(sender, instance, created, **kwargs):
    if not created:
        return

    Cart.objects.get_or_create(user=instance)
    NotificationPreference.objects.get_or_create(user=instance)
    Wishlist.objects.get_or_create(user=instance, wishlist_name="My Wishlist")
