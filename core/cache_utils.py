import logging
import re
import uuid
from django.apps import apps
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)

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

# Tokens to exclude from chatbot hints — too generic to be useful
_HINT_STOPWORDS = {
    "pro", "max", "plus", "new", "the", "and", "for", "with",
    "gen", "ver", "rev", "std", "ltd", "inc", "pvt",
}
_HINT_MIN_TOKEN_LENGTH = 3


# ---------------------------------------------------------------------------
# Fix 2 — Redis fallback wrapper
# ---------------------------------------------------------------------------

def _cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        logger.warning("Redis cache.get failed for key: %s", key)
        return default


def _cache_set(key, value, ttl):
    try:
        cache.set(key, value, ttl)
    except Exception:
        logger.warning("Redis cache.set failed for key: %s", key)


def _cache_delete(key):
    try:
        cache.delete(key)
    except Exception:
        logger.warning("Redis cache.delete failed for key: %s", key)


def _cache_get_or_set(key, loader_fn, ttl):
    """Get from cache, call loader_fn on miss, set result. Falls back to loader_fn if Redis is down."""
    try:
        value = cache.get(key)
        if value is not None:
            return value
        value = loader_fn()
        try:
            cache.set(key, value, ttl)
        except Exception:
            logger.warning("Redis cache.set failed for key: %s", key)
        return value
    except Exception:
        logger.warning("Redis unavailable, loading directly from DB for key: %s", key)
        return loader_fn()


# ---------------------------------------------------------------------------
# Namespace versioning
# ---------------------------------------------------------------------------

def _namespace_version_key(namespace):
    return f"cache_namespace:{namespace}:version"


def _get_namespace_version(namespace):
    version_key = _namespace_version_key(namespace)
    version = _cache_get(version_key)
    if version is None:
        version = "1"
        _cache_set(version_key, version, None)
    return version


def _namespaced_key(namespace, suffix):
    return f"{namespace}:v{_get_namespace_version(namespace)}:{suffix}"


def invalidate_cache_namespace(namespace):
    try:
        cache.set(_namespace_version_key(namespace), uuid.uuid4().hex, None)
    except Exception:
        logger.warning("Redis unavailable, could not invalidate namespace: %s", namespace)


# ---------------------------------------------------------------------------
# Catalog caches — these return ORM objects (used in templates directly)
# Low risk: Category/SubCategory are small, rarely change
# ---------------------------------------------------------------------------

def get_cached_active_categories():
    Category = apps.get_model("core", "Category")
    cache_key = _namespaced_key("catalog", "active_categories")
    return _cache_get_or_set(
        cache_key,
        lambda: list(Category.objects.filter(is_active=True)),
        CATALOG_CACHE_TTL_SECONDS,
    )


def get_cached_active_subcategories():
    SubCategory = apps.get_model("core", "SubCategory")
    cache_key = _namespaced_key("catalog", "active_subcategories")
    return _cache_get_or_set(
        cache_key,
        lambda: list(SubCategory.objects.filter(is_active=True)),
        CATALOG_CACHE_TTL_SECONDS,
    )


def get_cached_subcategory_options(category_slug=None):
    suffix = f"subcategory_options:{category_slug or 'all'}"
    cache_key = _namespaced_key("catalog", suffix)

    def _load():
        SubCategory = apps.get_model("core", "SubCategory")
        filters = {"is_active": True}
        if category_slug:
            filters["category__slug"] = category_slug
        return list(
            SubCategory.objects.filter(**filters).values("slug", "name").order_by("name")
        )

    return _cache_get_or_set(cache_key, _load, CATALOG_CACHE_TTL_SECONDS)


def get_cached_active_banners():
    Banner = apps.get_model("core", "Banner")
    cache_key = _namespaced_key("home", "active_banners")

    def _load():
        return list(
            Banner.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            ).order_by("start_date", "-id")
        )

    return _cache_get_or_set(cache_key, _load, HOME_BANNER_CACHE_TTL_SECONDS)


def get_cached_google_login_enabled():
    cache_key = _namespaced_key("auth", "google_login_enabled")

    def _load():
        try:
            from allauth.socialaccount.models import SocialApp
        except Exception:
            return False
        return SocialApp.objects.filter(provider="google").exists()

    return _cache_get_or_set(cache_key, _load, AUTH_CACHE_TTL_SECONDS)


# ---------------------------------------------------------------------------
# Fix 1 — Serialize ORM objects to dicts before caching
# ---------------------------------------------------------------------------

def _serialize_notification(n):
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "image_url": n.image_url,
        "redirect_url": n.redirect_url,
        "is_read": n.is_read,
        "created_at": n.created_at,
    }


def _serialize_wishlist(w):
    return {
        "id": w.id,
        "wishlist_name": w.wishlist_name,
        "item_count": w.item_count,
        "created_at": w.created_at,
    }


def _user_wishlist_cache_key(user_id):
    return f"user:{user_id}:wishlists"


def _header_context_cache_key(user_id):
    return f"header_context:{user_id}"


def get_cached_user_wishlists(user):
    if not getattr(user, "is_authenticated", False):
        return []

    Wishlist = apps.get_model("user", "Wishlist")
    cache_key = _user_wishlist_cache_key(user.id)

    def _load():
        qs = (
            Wishlist.objects.filter(user_id=user.id)
            .annotate(item_count=Count("items"))
            .order_by("-created_at")
        )
        return [_serialize_wishlist(w) for w in qs]

    return _cache_get_or_set(cache_key, _load, USER_WISHLISTS_CACHE_TTL_SECONDS)


def get_cached_header_context(user):
    if not getattr(user, "is_authenticated", False):
        return dict(_EMPTY_HEADER_CONTEXT)

    cache_key = _header_context_cache_key(user.id)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    Notification = apps.get_model("core", "Notification")
    CartItem = apps.get_model("user", "CartItem")

    user_wishlists = get_cached_user_wishlists(user)

    recent_notifications_qs = (
        Notification.objects.filter(user_id=user.id).order_by("-created_at")[:5]
    )

    context = {
        "unread_notification_count": Notification.objects.filter(
            user_id=user.id, is_read=False
        ).count(),
        "recent_notifications": [_serialize_notification(n) for n in recent_notifications_qs],
        "cart_count": CartItem.objects.filter(cart__user_id=user.id).count(),
        "wishlist_count": sum(w["item_count"] for w in user_wishlists),
        "user_wishlists": user_wishlists,
    }
    _cache_set(cache_key, context, HEADER_CONTEXT_TTL_SECONDS)
    return context


def invalidate_user_wishlist_cache(user_id):
    if user_id:
        _cache_delete(_user_wishlist_cache_key(user_id))


def invalidate_user_header_cache(user_id):
    if user_id:
        _cache_delete(_header_context_cache_key(user_id))


def invalidate_user_common_cache(user_id):
    invalidate_user_wishlist_cache(user_id)
    invalidate_user_header_cache(user_id)


# ---------------------------------------------------------------------------
# Chatbot hints — Fix 3: filter noisy tokens
# ---------------------------------------------------------------------------

CHATBOT_HINTS_CACHE_KEY = "chatbot:product_hints"
CHATBOT_HINTS_CACHE_TTL = 300


def get_cached_chatbot_product_hints():
    cached = _cache_get(CHATBOT_HINTS_CACHE_KEY)
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

    brands = (
        base_qs.exclude(brand__isnull=True).exclude(brand__exact="")
        .values_list("brand", flat=True).distinct()
    )
    product_names = (
        base_qs.exclude(name__isnull=True).exclude(name__exact="")
        .values_list("name", flat=True).distinct()
    )
    category_names = Category.objects.filter(is_active=True).values_list("name", flat=True)
    subcategory_names = SubCategory.objects.filter(is_active=True).values_list("name", flat=True)

    hints = set()

    # Brands and category names added whole (lowercased)
    for value in (*brands, *category_names, *subcategory_names):
        if value:
            token = value.lower().strip()
            if len(token) >= _HINT_MIN_TOKEN_LENGTH and token not in _HINT_STOPWORDS:
                hints.add(token)

    # Product names tokenized — filter noise
    for name in product_names:
        if name:
            for token in re.findall(r"[a-zA-Z]+", name.lower()):
                if (
                    len(token) >= _HINT_MIN_TOKEN_LENGTH
                    and token not in _HINT_STOPWORDS
                    and not token.isdigit()
                ):
                    hints.add(token)

    _cache_set(CHATBOT_HINTS_CACHE_KEY, hints, CHATBOT_HINTS_CACHE_TTL)
    return hints


def invalidate_chatbot_brands_cache():
    _cache_delete(CHATBOT_HINTS_CACHE_KEY)
