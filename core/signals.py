from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import (
    invalidate_cache_namespace,
    invalidate_user_header_cache,
)
from core.models import Banner, Category, Notification, SubCategory


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
@receiver(post_save, sender=SubCategory)
@receiver(post_delete, sender=SubCategory)
def invalidate_catalog_common_cache(sender, **kwargs):
    invalidate_cache_namespace("catalog")


@receiver(post_save, sender=Banner)
@receiver(post_delete, sender=Banner)
def invalidate_home_banner_cache(sender, **kwargs):
    invalidate_cache_namespace("home")


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def invalidate_notification_header_cache(sender, instance, **kwargs):
    invalidate_user_header_cache(instance.user_id)


try:
    from allauth.socialaccount.models import SocialApp
except Exception:
    SocialApp = None


if SocialApp is not None:

    @receiver(post_save, sender=SocialApp)
    @receiver(post_delete, sender=SocialApp)
    def invalidate_auth_common_cache(sender, **kwargs):
        invalidate_cache_namespace("auth")
