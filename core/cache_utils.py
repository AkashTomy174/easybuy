import re
import uuid
from django.apps import apps
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

CATALOG_CACHE_TTL_SECONDS = 300
HOME_BANNER_CACHE_TTL_SECONDS = 60
HEADER_CONTEXT_TTL_SECONDS = 30
AUTH_CACHE_TTL_SECONDS = 300
USER_WISHLISTS_CACHE_TTL_SECONDS = 120

_EMPTY_HEADER_CONTEXT = {
    "unread_notification_count": 0,
    "recent_notifications": [],
    "cart_count": 0,
    "wishlist_count": 0,
    "user_wishlists": [],
}

def _namespace_version_key(namespace):
    return f"cache_namespace:{namespace}:version"

def _get_namespace_version(namespace):
    version_key = _namespace_version_key(namespace)
    version = cache.get(version_key)
    if version is None:
        version = "1"
        cache.set(version_key, version, None)
    return version

def _namespaced_key(namespace, suffix):
    return f"{namespace}:v{_get_namespace_version(namespace)}:{suffix}"

def invalidate_cache_namespace(namespace):
    cache.set(_namespace_version_key(namespace), uuid.uuid4().hex, None)

def get_cached_active_categories():
    Category = apps.get_model("core", "Category")
    cache_key = _namespaced_key("catalog", "active_categories")
    return cache.get_or_set(
        cache_key,
        lambda: list(Category.objects.filter(is_active=True)),
        CATALOG_CACHE_TTL_SECONDS,
    )

def get_cached_active_subcategories():
    SubCategory = apps.get_model("core", "SubCategory")
    cache_key = _namespaced_key("catalog", "active_subcategories")
    return cache.get_or_set(
        cache_key,
        lambda: list(SubCategory.objects.filter(is_active=True)),
        CATALOG_CACHE_TTL_SECONDS,
    )

def get_cached_subcategory_options(category_slug=None):
    suffix = f"subcategory_options:{category_slug or 'all'}"
    cache_key = _namespaced_key("catalog", suffix)

    def _load_subcategories():
        SubCategory = apps.get_model("core", "SubCategory")
        filters = {"is_active": True}
        if category_slug:
            filters["category__slug"] = category_slug
        return list(
            SubCategory.objects.filter(**filters).values("slug", "name").order_by("name")
        )

    return cache.get_or_set(
        cache_key,
        _load_subcategories,
        CATALOG_CACHE_TTL_SECONDS,
    )

def get_cached_active_banners():
    Banner = apps.get_model("core", "Banner")
    cache_key = _namespaced_key("home", "active_banners")
    return cache.get_or_set(
        cache_key,
        lambda: list(
            Banner.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            ).order_by("start_date", "-id")
        ),
        HOME_BANNER_CACHE_TTL_SECONDS,
    )

def get_cached_google_login_enabled():
    cache_key = _namespaced_key("auth", "google_login_enabled")

    def _load_google_login_enabled():
        try:
            from allauth.socialaccount.models import SocialApp
        except Exception:
            return False
        return SocialApp.objects.filter(provider="google").exists()

    return cache.get_or_set(cache_key, _load_google_login_enabled, AUTH_CACHE_TTL_SECONDS)

def _user_wishlist_cache_key(user_id):
    return f"user:{user_id}:wishlists"

def _header_context_cache_key(user_id):
    return f"header_context:{user_id}"

def get_cached_user_wishlists(user):
    if not getattr(user, "is_authenticated", False):
        return []

    Wishlist = apps.get_model("user", "Wishlist")
    cache_key = _user_wishlist_cache_key(user.id)
    return cache.get_or_set(
        cache_key,
        lambda: list(
            Wishlist.objects.filter(user_id=user.id)
            .annotate(item_count=Count("items"))
            .order_by("-created_at")
        ),
        USER_WISHLISTS_CACHE_TTL_SECONDS,
    )

def get_cached_header_context(user):
    if not getattr(user, "is_authenticated", False):
        return dict(_EMPTY_HEADER_CONTEXT)

    cache_key = _header_context_cache_key(user.id)
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context

    Notification = apps.get_model("core", "Notification")
    CartItem = apps.get_model("user", "CartItem")

    user_wishlists = get_cached_user_wishlists(user)
    context = {
        "unread_notification_count": Notification.objects.filter(
            user_id=user.id, is_read=False
        ).count(),
        "recent_notifications": list(
            Notification.objects.filter(user_id=user.id).order_by("-created_at")[:5]
        ),
        "cart_count": CartItem.objects.filter(cart__user_id=user.id).count(),
        "wishlist_count": sum(wishlist.item_count for wishlist in user_wishlists),
        "user_wishlists": user_wishlists,
    }
    cache.set(cache_key, context, HEADER_CONTEXT_TTL_SECONDS)
    return context

def invalidate_user_wishlist_cache(user_id):
    if user_id:
        cache.delete(_user_wishlist_cache_key(user_id))

def invalidate_user_header_cache(user_id):
    if user_id:
        cache.delete(_header_context_cache_key(user_id))

def invalidate_user_common_cache(user_id):
    invalidate_user_wishlist_cache(user_id)
    invalidate_user_header_cache(user_id)

CHATBOT_HINTS_CACHE_KEY = "chatbot:product_hints"
CHATBOT_HINTS_CACHE_TTL = 300

def get_cached_chatbot_product_hints():
    cached = cache.get(CHATBOT_HINTS_CACHE_KEY)
    if cached is not None:
        return cached

    Product = apps.get_model("seller", "Product")
    Category = apps.get_model("core", "Category")
    SubCategory = apps.get_model("core", "SubCategory")

    base_qs = Product.objects.filter(
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED",
    )

    brands = base_qs.exclude(brand__isnull=True).exclude(brand__exact="") \
        .values_list("brand", flat=True).distinct()

    product_names = base_qs.exclude(name__isnull=True).exclude(name__exact="") \
        .values_list("name", flat=True).distinct()

    category_names = Category.objects.filter(is_active=True) \
        .values_list("name", flat=True)

    subcategory_names = SubCategory.objects.filter(is_active=True) \
        .values_list("name", flat=True)

    hints = set()
    for value in (*brands, *category_names, *subcategory_names):
        if value:
            hints.add(value.lower().strip())

    # for product names, tokenize each word so "boAt Rockerz 255" adds "boat", "rockerz", "255"
    for name in product_names:
        if name:
            for token in re.findall(r"[a-zA-Z0-9]+", name.lower()):
                if len(token) > 2:
                    hints.add(token)

    cache.set(CHATBOT_HINTS_CACHE_KEY, hints, CHATBOT_HINTS_CACHE_TTL)
    return hints

def invalidate_chatbot_brands_cache():
    cache.delete(CHATBOT_HINTS_CACHE_KEY)
