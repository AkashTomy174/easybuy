from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from core.decorators import role_required
from easybuy_admin.models import Coupon
from seller.models import Product, ProductVariant, ProductImage
from .models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    Review,
    Wishlist,
    WishlistItem,
    ReviewImage,
    ReviewVideo,
    ReviewHelpful,
    NotificationPreference,
    SavedCard,
    ReturnRequest,
    ReturnRequestImage,
    PaymentTransaction,
)
from core.models import SubCategory, Category, Address, Notification
import json
from django.http import Http404
from django.db.models import Q, Avg, Count, Prefetch
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum
import uuid
import razorpay
import logging
from django.conf import settings
from django.http import HttpResponse
from decimal import Decimal as DzDecimal
from core.whatsapp_utils import WhatsAppNotifier
from core.services import create_notification
from core.cache_utils import (
    get_cached_active_banners as _get_cached_active_banners,
    get_cached_active_categories as _get_cached_active_categories,
    get_cached_active_subcategories as _get_cached_active_subcategories,
    get_cached_subcategory_options,
    get_cached_user_wishlists as _get_user_wishlists,
    invalidate_user_header_cache,
)
from django.views.decorators.csrf import csrf_exempt


logger = logging.getLogger(__name__)
CHECKOUT_PROMO_SESSION_KEY = "checkout_promo_code"
RECENTLY_VIEWED_VARIANTS_SESSION_KEY = "recently_viewed_variant_ids"
MAX_RECENTLY_VIEWED_VARIANTS = 10
MONEY_PRECISION = DzDecimal("0.01")
DEFAULT_ADDRESS_COUNTRY = "India"
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_RETURN_IMAGES = 5


class RazorpayOrderError(Exception):
    def __init__(self, payload, status_code):
        super().__init__(payload.get("error", "Razorpay order creation failed"))
        self.payload = payload
        self.status_code = status_code


def _restock_order_item(order_item):
    if not order_item.stock_deducted:
        return

    ProductVariant.objects.filter(pk=order_item.variant_id).update(
        stock_quantity=F("stock_quantity") + order_item.quantity
    )
    order_item.stock_deducted = False
    order_item.save(update_fields=["stock_deducted"])


def _deduct_order_item_stock(order_item):
    if order_item.stock_deducted:
        return True

    updated_rows = ProductVariant.objects.filter(
        pk=order_item.variant_id, stock_quantity__gte=order_item.quantity
    ).update(stock_quantity=F("stock_quantity") - order_item.quantity)
    if not updated_rows:
        return False

    order_item.stock_deducted = True
    order_item.save(update_fields=["stock_deducted"])
    return True


def _record_payment_transaction(order, transaction_id, status, gateway_response):
    transaction_obj, created = PaymentTransaction.objects.get_or_create(
        order=order,
        transaction_id=transaction_id,
        defaults={
            "payment_gateway": "Razorpay",
            "amount": order.total_amount,
            "status": status,
            "gateway_response": gateway_response,
        },
    )
    if not created:
        update_fields = []
        if transaction_obj.status != status:
            transaction_obj.status = status
            update_fields.append("status")
        if transaction_obj.gateway_response != gateway_response:
            transaction_obj.gateway_response = gateway_response
            update_fields.append("gateway_response")
        if update_fields:
            transaction_obj.save(update_fields=update_fields)
    return transaction_obj


def _finalize_online_order(
    order, razorpay_payment_id, gateway_response, *, clear_cart=False
):
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .prefetch_related("items__variant__product")
            .get(pk=order.pk)
        )

        order_updates = []
        if razorpay_payment_id and order.razorpay_payment_id != razorpay_payment_id:
            order.razorpay_payment_id = razorpay_payment_id
            order_updates.append("razorpay_payment_id")

        if order.payment_status == "PAID":
            if order_updates:
                order.save(update_fields=order_updates)
            _record_payment_transaction(
                order,
                razorpay_payment_id,
                "PAID",
                gateway_response,
            )
            if clear_cart:
                Cart.objects.filter(user=order.user).delete()
                logger.info("Cart cleared for user %s", order.user_id)
            return order, False

        order.payment_status = "PAID"
        order.order_status = "CONFIRMED"
        order.payment_method = "ONLINE"
        order_updates.extend(["payment_status", "order_status", "payment_method"])
        order.save(update_fields=order_updates)
        logger.info("Order %s marked as PAID", order.order_number)

        for item in order.items.all():
            ProductVariant.objects.select_for_update().filter(
                pk=item.variant_id
            ).first()
            if not _deduct_order_item_stock(item):
                raise ValueError(f"Insufficient stock for {item.variant.product.name}")
            logger.info(
                "Stock updated for variant %s: -%s", item.variant.id, item.quantity
            )

        _record_payment_transaction(
            order,
            razorpay_payment_id,
            "PAID",
            gateway_response,
        )

        if clear_cart:
            Cart.objects.filter(user=order.user).delete()
            logger.info("Cart cleared for user %s", order.user_id)

        _send_order_confirmation(order)
        logger.info("Order confirmation notification sent for %s", order.order_number)
        return order, True


def _extract_razorpay_payment_details(payload):
    payload = payload or {}
    nested_payload = payload.get("payload") or {}
    payment_entity = (nested_payload.get("payment") or {}).get("entity") or {}
    order_entity = (nested_payload.get("order") or {}).get("entity") or {}
    razorpay_order_id = str(
        payment_entity.get("order_id") or order_entity.get("id") or ""
    ).strip()
    razorpay_payment_id = str(payment_entity.get("id") or "").strip()
    return razorpay_order_id, razorpay_payment_id, payment_entity


def _get_primary_image_for_variant(variant):
    preview_image = getattr(variant, "preview_image", None)
    if preview_image is not None:
        return preview_image

    primary_images = getattr(variant, "primary_images", None)
    if primary_images is not None:
        for image in primary_images:
            if image.image:
                return image

    images = getattr(variant, "ordered_images", None)
    if images is None:
        images = list(variant.images.all())
    for image in images:
        if image.image and image.is_primary:
            return image
    for image in images:
        if image.image:
            return image
    return None


def _primary_variant_image_prefetch():
    return Prefetch(
        "images",
        queryset=ProductImage.objects.filter(is_primary=True).only(
            "id", "variant_id", "image", "alt_text", "is_primary"
        ),
        to_attr="primary_images",
    )


def _with_primary_variant_images(queryset):
    return queryset.prefetch_related(_primary_variant_image_prefetch())


def _ensure_variant_preview_images(variants):
    variants = list(variants)
    fallback_variant_ids = []

    for variant in variants:
        primary_images = getattr(variant, "primary_images", None)
        variant.preview_image = next(
            (image for image in (primary_images or []) if getattr(image, "image", None)),
            None,
        )
        if variant.preview_image is None:
            fallback_variant_ids.append(variant.id)

    if not fallback_variant_ids:
        return variants

    fallback_images = {}
    for image in (
        ProductImage.objects.filter(variant_id__in=fallback_variant_ids)
        .only("id", "variant_id", "image", "alt_text", "is_primary")
        .order_by("variant_id", "-is_primary", "id")
    ):
        if image.image and image.variant_id not in fallback_images:
            fallback_images[image.variant_id] = image

    for variant in variants:
        if variant.preview_image is None:
            variant.preview_image = fallback_images.get(variant.id)

    return variants


def _get_wishlist_variant_ids(user, variant_ids):
    if not getattr(user, "is_authenticated", False) or not variant_ids:
        return set()
    return set(
        WishlistItem.objects.filter(
            wishlist__user=user, variant_id__in=variant_ids
        ).values_list("variant_id", flat=True)
    )


def _build_product_data(variants, wishlist_variant_ids=None):
    wishlist_variant_ids = wishlist_variant_ids or set()
    variants = _ensure_variant_preview_images(variants)
    return [
        {
            "variant": variant,
            "image": _get_primary_image_for_variant(variant),
            "in_wishlist": variant.id in wishlist_variant_ids,
        }
        for variant in variants
    ]


def _get_recently_viewed_variant_ids(request):
    raw_ids = request.session.get(RECENTLY_VIEWED_VARIANTS_SESSION_KEY, [])
    cleaned_ids = []
    for raw_id in raw_ids:
        try:
            cleaned_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    return cleaned_ids


def _track_recently_viewed_variant(request, variant):
    if not variant:
        return

    variant_id = int(variant.id)
    recent_ids = [
        existing_id
        for existing_id in _get_recently_viewed_variant_ids(request)
        if existing_id != variant_id
    ]
    recent_ids.insert(0, variant_id)
    request.session[RECENTLY_VIEWED_VARIANTS_SESSION_KEY] = recent_ids[
        :MAX_RECENTLY_VIEWED_VARIANTS
    ]
    request.session.modified = True


def _get_recently_viewed_variants(request, *, limit=6, exclude_variant_ids=None):
    exclude_variant_ids = {
        int(variant_id)
        for variant_id in (exclude_variant_ids or [])
        if str(variant_id).isdigit()
    }
    ordered_ids = [
        variant_id
        for variant_id in _get_recently_viewed_variant_ids(request)
        if variant_id not in exclude_variant_ids
    ]
    if not ordered_ids:
        return []

    recent_variants = (
        _with_primary_variant_images(_customer_visible_variants_queryset())
        .filter(id__in=ordered_ids)
        .select_related(
            "product",
            "product__seller",
            "product__subcategory",
            "product__subcategory__category",
        )
    )
    variant_map = {variant.id: variant for variant in recent_variants}
    ordered_variants = [
        variant_map[variant_id]
        for variant_id in ordered_ids
        if variant_id in variant_map
    ]
    return ordered_variants[:limit]


def _customer_visible_variants_queryset():
    return ProductVariant.objects.select_related("product", "product__seller").filter(
        product__is_active=True,
        product__approval_status="APPROVED",
        product__seller__status="APPROVED",
    )


def _get_customer_visible_variant_or_404(variant_id):
    return get_object_or_404(_customer_visible_variants_queryset(), id=variant_id)


def _is_variant_customer_visible(variant):
    product = getattr(variant, "product", None)
    seller = getattr(product, "seller", None) if product is not None else None
    return bool(
        product
        and seller
        and product.is_active
        and product.approval_status == "APPROVED"
        and seller.status == "APPROVED"
    )


def _get_return_eligibility(order_item):
    if order_item.status != "DELIVERED":
        return {
            "eligible": False,
            "expired": False,
            "message": "Item must be delivered to be returned.",
        }

    if ReturnRequest.objects.filter(order_item=order_item).exists():
        return {
            "eligible": False,
            "expired": False,
            "message": "Return already requested.",
        }

    product = order_item.variant.product
    if not product.is_returnable:
        return {
            "eligible": False,
            "expired": False,
            "message": "This product is not eligible for return.",
        }

    ref_date = order_item.delivered_at or order_item.order.ordered_at
    if not ref_date:
        return {
            "eligible": False,
            "expired": False,
            "message": "Return details are unavailable for this item.",
        }

    days_passed = (timezone.now() - ref_date).days
    if days_passed > product.return_days:
        return {
            "eligible": False,
            "expired": True,
            "message": "The return window has expired for this item.",
        }

    return {"eligible": True, "expired": False, "message": ""}


def _normalize_address_payload(request):
    return {
        "full_name": (request.POST.get("fullname") or "").strip(),
        "phone_number": (request.POST.get("phone") or "").strip(),
        "pincode": (request.POST.get("pincode") or "").strip(),
        "locality": (request.POST.get("locality") or "").strip(),
        "house_info": (request.POST.get("house_info") or "").strip(),
        "city": (request.POST.get("city") or "").strip(),
        "state": (request.POST.get("state") or "").strip(),
        "country": (request.POST.get("country") or DEFAULT_ADDRESS_COUNTRY).strip(),
        "address_type": (request.POST.get("address_type") or "").strip(),
        "is_default": request.POST.get("is_default") == "on",
    }


def _validate_image_file(file_obj, *, label):
    content_type = (getattr(file_obj, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return f"{label} must be a JPG, PNG, GIF, or WEBP image."
    if file_obj.size > MAX_IMAGE_UPLOAD_BYTES:
        return f"{label} must be smaller than 5MB."
    return ""


# home related diplaying mainly
def home_view(request):
    if request.user.is_authenticated:
        if request.user.role == "ADMIN":
            return redirect("admin_dashboard")
        elif request.user.role == "SELLER":
            return redirect("seller_dashboard")

    categories = _get_cached_active_categories()
    active_banners = _get_cached_active_banners()
    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related("product", "product__seller")
        .order_by("-id")[:8]
    )
    variant_list = list(variants)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    recently_viewed_variants = _get_recently_viewed_variants(request, limit=8)
    recent_wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in recently_viewed_variants]
    )
    user_wishlists = _get_user_wishlists(request.user)
    product_data = _build_product_data(variant_list, wishlist_variant_ids)
    recent_product_data = _build_product_data(
        recently_viewed_variants, recent_wishlist_variant_ids
    )
    return render(
        request,
        "core/home.html",
        {
            "active_banners": active_banners,
            "categories": categories,
            "product_data": product_data,
            "recent_product_data": recent_product_data,
            "wishlists": user_wishlists,
        },
    )


def all_categories(request):
    categories = _get_cached_active_categories()
    return render(request, "core/all_categories.html", {"categories": categories})


def all_products(request):
    icategory = request.GET.get("category")
    isubCategory = request.GET.get("subcategory")
    ibrand = request.GET.getlist("brand")
    min_price = request.GET.get("min")
    max_price = request.GET.get("max")
    iprod = request.GET.get("q")
    sort = request.GET.get("sort", "newest")
    min_rating = request.GET.get("rating")
    availability = request.GET.get("availability")

    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related(
            "product",
            "product__seller",
            "product__subcategory",
            "product__subcategory__category",
        )
    )

    # Base query for brands - start with all approved products
    brand_query = Product.objects.filter(
        is_active=True, approval_status="APPROVED", seller__status="APPROVED"
    )

    if icategory:
        variants = variants.filter(product__subcategory__category__slug=icategory)
        brand_query = brand_query.filter(subcategory__category__slug=icategory)
    if isubCategory:
        variants = variants.filter(product__subcategory__slug=isubCategory)
        brand_query = brand_query.filter(subcategory__slug=isubCategory)
    if ibrand:
        variants = variants.filter(product__brand__in=ibrand)
    if iprod:
        search_query = iprod.strip()
        variants = variants.filter(
            Q(product__name__icontains=search_query)
            | Q(product__description__icontains=search_query)
            | Q(product__brand__icontains=search_query)
        )
        brand_query = brand_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )
    if min_price:
        min_price = float(min_price)
        variants = variants.filter(selling_price__gte=min_price)
    if max_price:
        max_price = float(max_price)
        variants = variants.filter(selling_price__lte=max_price)

    # Rating filter
    if min_rating:
        try:
            min_rating = int(min_rating)
            # Get products with average rating >= min_rating
            product_ids = (
                Product.objects.filter(
                    is_active=True,
                    approval_status="APPROVED",
                    seller__status="APPROVED",
                )
                .annotate(avg_rating=Avg("reviews__rating"))
                .filter(avg_rating__gte=min_rating)
                .values_list("id", flat=True)
            )
            variants = variants.filter(product_id__in=product_ids)
        except (ValueError, TypeError):
            pass

    # Availability filter
    if availability == "in_stock":
        variants = variants.filter(stock_quantity__gt=0)
    elif availability == "out_of_stock":
        variants = variants.filter(stock_quantity=0)

    # Sorting
    if sort == "price_low":
        variants = variants.order_by("selling_price")
    elif sort == "price_high":
        variants = variants.order_by("-selling_price")
    elif sort == "name_asc":
        variants = variants.order_by("product__name")
    elif sort == "name_desc":
        variants = variants.order_by("-product__name")
    elif sort == "best_rated":
        # Annotate with average rating and sort
        variants = variants.annotate(
            avg_rating=Avg("product__reviews__rating")
        ).order_by("-avg_rating", "-id")
    elif sort == "most_popular":
        # Sort by total sales
        variants = variants.annotate(total_sold=Sum("orderitem__quantity")).order_by(
            "-total_sold", "-id"
        )
    else:
        variants = variants.order_by("-id")

    # Get brands based on current filters (category/subcategory/search)
    all_brands = (
        brand_query.values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
    )

    paginator = Paginator(variants, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    variant_list = list(page_obj.object_list)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    page_obj.object_list = _build_product_data(variant_list, wishlist_variant_ids)

    categories = _get_cached_active_categories()
    subcategories = _get_cached_active_subcategories()
    user_wishlists = _get_user_wishlists(request.user)

    context = {
        "page_obj": page_obj,
        "all_brands": all_brands,
        "categories": categories,
        "subcategories": subcategories,
        "selected_category": icategory or "",
        "selected_subcategory": isubCategory or "",
        "selected_brands": ibrand,
        "selected_min_price": min_price or "",
        "selected_max_price": max_price or "",
        "selected_product": iprod or "",
        "selected_sort": sort,
        "selected_rating": min_rating or "",
        "selected_availability": availability or "",
        "wishlists": user_wishlists,
    }
    return render(request, "user/all_products.html", context)


def new_arrival(request):
    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related("product", "product__seller")
        .order_by("-id")
    )
    paginator = Paginator(variants, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    variant_list = list(page_obj.object_list)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    page_obj.object_list = _build_product_data(variant_list, wishlist_variant_ids)
    user_wishlists = _get_user_wishlists(request.user)

    return render(
        request,
        "user/new_arrivals.html",
        {"page_obj": page_obj, "wishlists": user_wishlists},
    )


def category_products(request, slug=None, id=None):
    if slug:
        categories = get_object_or_404(Category, slug=slug, is_active=True)
    elif id:
        categories = get_object_or_404(Category, id=id, is_active=True)
    else:
        from django.http import Http404

        raise Http404("Category not found")

    subcategory = SubCategory.objects.filter(category=categories, is_active=True)
    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__subcategory__category=categories,
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related("product", "product__seller")
        .order_by("-id")
    )
    paginator = Paginator(variants, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    variant_list = list(page_obj.object_list)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    page_obj.object_list = _build_product_data(variant_list, wishlist_variant_ids)

    return render(
        request,
        "core/category_products.html",
        {
            "categories": categories,
            "subcategory": subcategory,
            "page_obj": page_obj,
            "active_sub": None,
        },
    )


def subcategory_products(request, slug=None, id=None):
    if slug:
        current_sub = get_object_or_404(SubCategory, slug=slug, is_active=True)
    elif id:
        current_sub = get_object_or_404(SubCategory, id=id, is_active=True)
    else:
        from django.http import Http404

        raise Http404("Subcategory not found")

    categories = current_sub.category
    subcategory = SubCategory.objects.filter(category=categories, is_active=True)
    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__subcategory=current_sub,
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related("product", "product__seller")
        .order_by("-id")
    )
    paginator = Paginator(variants, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    variant_list = list(page_obj.object_list)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    page_obj.object_list = _build_product_data(variant_list, wishlist_variant_ids)

    return render(
        request,
        "core/category_products.html",
        {
            "categories": categories,
            "subcategory": subcategory,
            "page_obj": page_obj,
            "active_sub": current_sub.id,
        },
    )


def product_detail(request, slug=None, id=None):
    if slug:
        product = (
            Product.objects.filter(
                slug=slug,
                is_active=True,
                approval_status="APPROVED",
                seller__status="APPROVED",
            )
            .prefetch_related(
                "variants__images",
                "variants__variantattributebridge_set__option",
            )
            .first()
        )
    elif id:
        product = (
            Product.objects.filter(
                id=id,
                is_active=True,
                approval_status="APPROVED",
                seller__status="APPROVED",
            )
            .prefetch_related(
                "variants__images",
                "variants__variantattributebridge_set__option",
            )
            .first()
        )
    else:
        product = None

    if not product:
        return render(
            request, "user/product_details.html", {"error": "Product not found"}
        )

    related_products = (
        Product.objects.prefetch_related("variants__images")
        .filter(
            subcategory_id=product.subcategory_id,
            is_active=True,
            approval_status="APPROVED",
            seller__status="APPROVED",
        )
        .exclude(slug=product.slug)[:4]
    )

    reviews = list(
        Review.objects.select_related("user")
        .prefetch_related("images", "videos")
        .filter(product=product)
        .order_by("-created_at")[:5]
    )
    all_reviews = Review.objects.filter(product=product)
    avg_rating = all_reviews.aggregate(Avg("rating"))["rating__avg"] or 0
    total_reviews = all_reviews.count()

    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in all_reviews:
        rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1

    rating_breakdown = []
    for rating in [5, 4, 3, 2, 1]:
        count = rating_counts.get(rating, 0)
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_breakdown.append(
            {"rating": rating, "count": count, "percentage": round(percentage, 1)}
        )

    existing_review = None

    wishlist_variant_ids = set()
    user_helpful_votes = set()
    if request.user.is_authenticated:
        existing_review = Review.objects.filter(
            user=request.user, product=product
        ).first()

        variant_ids = [v.id for v in product.variants.all()]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user, variant_id__in=variant_ids
        ).values_list("variant_id", flat=True)
        wishlist_variant_ids = set(wishlist_items)
        review_ids = [r.id for r in reviews]
        review_user_ids = [r.user_id for r in reviews]
        verified_users = set(
            OrderItem.objects.filter(
                order__user_id__in=review_user_ids,
                variant__product=product,
                order__order_status="DELIVERED",
            )
            .values_list("order__user_id", flat=True)
            .distinct()
        )
        user_helpful_votes = set(
            ReviewHelpful.objects.filter(
                user=request.user, review_id__in=review_ids
            ).values_list("review_id", flat=True)
        )

        for review in reviews:
            review.is_verified_purchase = review.user_id in verified_users
            review.user_voted_helpful = review.id in user_helpful_votes

    selected_variant = product.variants.first()
    requested_variant_id = str(request.GET.get("variant", "")).strip()
    if requested_variant_id:
        selected_variant = next(
            (
                variant
                for variant in product.variants.all()
                if str(variant.id) == requested_variant_id
            ),
            selected_variant,
        )
    _track_recently_viewed_variant(request, selected_variant)
    selected_variant_images = (
        list(selected_variant.images.all()) if selected_variant else []
    )
    selected_variant_image = None
    for image in selected_variant_images:
        if image.image and image.is_primary:
            selected_variant_image = image
            break
    if not selected_variant_image:
        for image in selected_variant_images:
            if image.image:
                selected_variant_image = image
                break

    context = {
        "product": product,
        "selected_variant": selected_variant,
        "selected_variant_image": selected_variant_image,
        "selected_variant_image_count": len(selected_variant_images),
        "related_products": related_products,
        "reviews": reviews,
        "avg_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews,
        "rating_breakdown": rating_breakdown,
        "existing_review": existing_review,
        "wishlist_variant_ids": list(wishlist_variant_ids),
        "wishlists": _get_user_wishlists(request.user),
    }
    return render(
        request,
        "user/product_details.html",
        context,
    )


# for reviews sections
@login_required
@role_required(allowed_roles=["CUSTOMER"])
def add_reviews(request, variant_id):

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"), id=variant_id
    )

    product = variant.product
    user = request.user

    has_purchased = OrderItem.objects.filter(
        order__user=user, variant__product=product, order__order_status="DELIVERED"
    ).exists()

    if not has_purchased:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "You can only review products you have purchased and received.",
                }
            )
        messages.error(
            request, "You can only review products you have purchased and received."
        )
        return redirect("product_detail_user", slug=product.slug)

    if Review.objects.filter(user=user, product=product).exists():
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "You have already reviewed this product."}
            )
        messages.error(request, "You have already reviewed this product.")
        return redirect("product_detail_user", slug=product.slug)

    if request.method == "POST":
        try:
            rating = request.POST.get("rating")
            comment = request.POST.get("comment", "").strip()

            try:
                rating = int(rating)
            except (ValueError, TypeError):
                messages.error(request, "Invalid rating.")
                return redirect("product_detail_user", slug=product.slug)

            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5.")
                return redirect("product_detail_user", slug=product.slug)

            if not comment:
                messages.error(request, "Comment is required.")
                return redirect("product_detail_user", slug=product.slug)

            if len(comment) > 1000:
                messages.error(request, "Comment is too long (max 1000 characters).")
                return redirect("product_detail_user", slug=product.slug)

            review = Review.objects.create(
                user=user, product=product, rating=rating, comment=comment
            )

            # Handle image uploads
            images = request.FILES.getlist("images")
            if len(images) > 5:
                messages.warning(
                    request, "Maximum 5 images allowed. Only first 5 were uploaded."
                )
                images = images[:5]

            for image in images:
                if image.size > 5 * 1024 * 1024:  # 5MB limit
                    messages.warning(
                        request, f"Image {image.name} exceeds 5MB and was skipped."
                    )
                    continue
                ReviewImage.objects.create(review=review, image=image)

            # Handle video uploads
            videos = request.FILES.getlist("videos")
            if len(videos) > 2:
                messages.warning(
                    request, "Maximum 2 videos allowed. Only first 2 were uploaded."
                )
                videos = videos[:2]

            for video in videos:
                if video.size > 50 * 1024 * 1024:  # 50MB limit
                    messages.warning(
                        request, f"Video {video.name} exceeds 50MB and was skipped."
                    )
                    continue
                ReviewVideo.objects.create(review=review, video=video)

            messages.success(request, "Thank you for your review!")
            return redirect("product_detail_user", slug=product.slug)
        except Exception as e:
            messages.error(request, "An error occurred while submitting your review.")
            return redirect("product_detail_user", slug=product.slug)

    context = {"product": product, "variant": variant}

    return render(request, "user/add_review.html", context)


def check_purchase_status(request, variant_id):
    if request.method != "GET":
        return JsonResponse({"message": "Invalid request"}, status=400)

    # Check if user is authenticated and is a customer
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "has_purchased": False,
                "has_reviewed": False,
                "can_review": False,
                "message": "Please login to review",
            }
        )

    if request.user.role != "CUSTOMER":
        return JsonResponse(
            {
                "has_purchased": False,
                "has_reviewed": False,
                "can_review": False,
                "message": "Only customers can review products",
            }
        )

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"), id=variant_id
    )
    product = variant.product
    user = request.user
    has_purchased = OrderItem.objects.filter(
        order__user=user, variant__product=product, order__order_status="DELIVERED"
    ).exists()
    has_reviewed = Review.objects.filter(user=user, product=product).exists()
    return JsonResponse(
        {
            "has_purchased": has_purchased,
            "has_reviewed": has_reviewed,
            "can_review": has_purchased and not has_reviewed,
        }
    )


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def reviews(request, variant_id):

    user = request.user

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product").prefetch_related("images"),
        id=variant_id,
    )

    sort_by = request.GET.get("sort", "recent")

    reviews_qs = (
        Review.objects.select_related("user")
        .prefetch_related("images", "videos")
        .filter(product=variant.product)
    )

    # Sorting
    if sort_by == "helpful":
        reviews_qs = reviews_qs.order_by("-helpful_count", "-created_at")
    elif sort_by == "rating_high":
        reviews_qs = reviews_qs.order_by("-rating", "-created_at")
    elif sort_by == "rating_low":
        reviews_qs = reviews_qs.order_by("rating", "-created_at")
    else:  # recent
        reviews_qs = reviews_qs.order_by("-created_at")

    # Optimize verified purchase check
    review_ids = list(reviews_qs.values_list("id", flat=True))
    review_user_ids = list(reviews_qs.values_list("user_id", flat=True))
    verified_users = set(
        OrderItem.objects.filter(
            order__user_id__in=review_user_ids,
            variant__product=variant.product,
            order__order_status="DELIVERED",
        )
        .values_list("order__user_id", flat=True)
        .distinct()
    )

    # Check if current user voted helpful
    user_helpful_votes = set(
        ReviewHelpful.objects.filter(user=user, review_id__in=review_ids).values_list(
            "review_id", flat=True
        )
    )

    for review in reviews_qs:
        review.is_verified_purchase = review.user_id in verified_users
        review.user_voted_helpful = review.id in user_helpful_votes

    paginator = Paginator(reviews_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "variant": variant,
        "product": variant.product,
        "user": user,
        "sort_by": sort_by,
    }

    return render(request, "user/reviews.html", context)


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product

    if request.method == "POST":
        try:
            rating = request.POST.get("rating")
            comment = request.POST.get("comment", "").strip()

            try:
                rating = int(rating)
            except (ValueError, TypeError):
                messages.error(request, "Invalid rating.")
                return redirect("product_detail_user", slug=product.slug)

            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5.")
                return redirect("product_detail_user", slug=product.slug)

            if not comment:
                messages.error(request, "Comment is required.")
                return redirect("product_detail_user", slug=product.slug)

            if len(comment) > 1000:
                messages.error(request, "Comment is too long (max 1000 characters).")
                return redirect("product_detail_user", slug=product.slug)

            review.rating = rating
            review.comment = comment
            review.save()

            messages.success(request, "Review updated successfully!")
            return redirect("product_detail_user", slug=product.slug)
        except Exception as e:
            messages.error(request, "An error occurred while updating your review.")
            return redirect("product_detail_user", slug=product.slug)

    variant = product.variants.first()
    context = {"product": product, "variant": variant, "review": review}
    return render(request, "user/edit_review.html", context)


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def delete_review(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    review = get_object_or_404(Review, id=review_id, user=request.user)
    product_slug = review.product.slug
    review.delete()

    messages.success(request, "Review deleted successfully.")
    return JsonResponse(
        {"success": True, "redirect_url": f"/user/products/{product_slug}/"}
    )


# cart related
@login_required
@role_required(allowed_roles=["SELLER", "CUSTOMER"])
def addtocart(request, id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    variant = _get_customer_visible_variant_or_404(id)

    if variant.stock_quantity <= 0:
        return JsonResponse({"message": "Out of stock"}, status=400)

    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"message": "Login required"}, status=401)

    cart, _ = Cart.objects.get_or_create(user=user)

    cartitem, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={"quantity": 1, "price_at_time": variant.selling_price},
    )

    if not created:
        if cartitem.quantity + 1 <= variant.stock_quantity:
            cartitem.quantity += 1
            cartitem.save()
        else:
            return JsonResponse(
                {"message": f"Only {variant.stock_quantity} items available"},
                status=400,
            )

    total = sum(item.quantity * item.price_at_time for item in cart.items.all())
    cart.total_amount = total
    cart_count = cart.items.count()
    cart.save()
    from core.notifications import schedule_cart_reminder

    schedule_cart_reminder(request.user)

    return JsonResponse(
        {
            "success": True,
            "message": "Item added to cart successfully",
            "quantity": cartitem.quantity,
            "total": cart.total_amount,
            "cart_count": cart_count,
        }
    )


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def cart_view(request):
    if not request.user.is_authenticated:
        return render(
            request, "user/cart.html", {"error": "Please log in to view your cart."}
        )

    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related("variant__product").all()
    return render(request, "user/cart.html", {"cart": cart, "items": items})


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def update_cart_quantity(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        delta = data.get("delta", 0)
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid data"}, status=400)

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    variant = cart_item.variant
    cart = cart_item.cart

    if not _is_variant_customer_visible(variant):
        return JsonResponse(
            {
                "message": "This product is no longer available",
                "success": False,
            },
            status=400,
        )

    new_quantity = cart_item.quantity + delta

    if new_quantity <= 0:
        cart_item.delete()
        message = "Item removed from cart"
        new_quantity = 0
    elif new_quantity > variant.stock_quantity:
        return JsonResponse(
            {
                "message": f"Only {variant.stock_quantity} items available",
                "success": False,
            },
            status=400,
        )
    else:
        cart_item.quantity = new_quantity
        cart_item.save()
        message = "Quantity updated"

    total = sum(item.quantity * item.price_at_time for item in cart.items.all())
    cart.total_amount = total
    cart.save()

    cart_count = cart.items.count()
    if cart_count > 0:
        from core.notifications import schedule_cart_reminder

        schedule_cart_reminder(request.user)

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "quantity": new_quantity,
            "total": cart.total_amount,
            "cart_count": cart_count,
        }
    )


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def remove_from_cart(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = cart_item.cart
    cart_item.delete()

    total = sum(item.quantity * item.price_at_time for item in cart.items.all())
    cart.total_amount = total
    cart.save()

    cart_count = cart.items.count()

    return JsonResponse(
        {
            "success": True,
            "message": "Item removed from cart",
            "total": cart.total_amount,
            "cart_count": cart_count,
        }
    )


# filtering related
def filtering(request):
    icategory = request.GET.get("category")
    isubCategory = request.GET.get("subcategory")
    ibrand = request.GET.getlist("brand")
    min_price = request.GET.get("min")
    max_price = request.GET.get("max")
    iprod = request.GET.get("q") or request.GET.get("product")
    sort = request.GET.get("sort", "newest")

    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related(
            "product",
            "product__seller",
            "product__subcategory",
            "product__subcategory__category",
        )
    )

    brand_query = Product.objects.filter(
        is_active=True, approval_status="APPROVED", seller__status="APPROVED"
    )

    if icategory:
        variants = variants.filter(product__subcategory__category__slug=icategory)
        brand_query = brand_query.filter(subcategory__category__slug=icategory)
    if isubCategory:
        variants = variants.filter(product__subcategory__slug=isubCategory)
        brand_query = brand_query.filter(subcategory__slug=isubCategory)

    if ibrand:
        variants = variants.filter(product__brand__in=ibrand)

    if iprod:
        search_query = iprod.strip()
        variants = variants.filter(
            Q(product__name__icontains=search_query)
            | Q(product__description__icontains=search_query)
            | Q(product__brand__icontains=search_query)
        )
        brand_query = brand_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )

    if min_price:
        min_price = float(min_price)
        variants = variants.filter(selling_price__gte=min_price)

    if max_price:
        max_price = float(max_price)
        variants = variants.filter(selling_price__lte=max_price)

    if sort == "price_low":
        variants = variants.order_by("selling_price")
    elif sort == "price_high":
        variants = variants.order_by("-selling_price")
    elif sort == "name_asc":
        variants = variants.order_by("product__name")
    elif sort == "name_desc":
        variants = variants.order_by("-product__name")
    else:
        variants = variants.order_by("-id")

    all_brands = (
        brand_query.values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
    )

    categories = _get_cached_active_categories()
    subcategories = _get_cached_active_subcategories()

    variant_list = list(variants)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    user_wishlists = _get_user_wishlists(request.user)
    product_data = _build_product_data(variant_list, wishlist_variant_ids)

    context = {
        "products": product_data,
        "all_brands": all_brands,
        "categories": categories,
        "subcategories": subcategories,
        "selected_category": icategory or "",
        "selected_subcategory": isubCategory or "",
        "selected_brands": ibrand,
        "selected_min_price": min_price or "",
        "selected_max_price": max_price or "",
        "selected_product": iprod or "",
        "selected_sort": sort,
        "wishlists": user_wishlists,
    }

    return render(request, "user/filter.html", context)


def best_seller(request):
    variants = _with_primary_variant_images(
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .annotate(total_sold=Sum("orderitem__quantity"))
        .filter(total_sold__gt=0)
        .select_related("product", "product__seller")
        .order_by("-total_sold")
    )
    paginator = Paginator(variants, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    variant_list = list(page_obj.object_list)
    wishlist_variant_ids = _get_wishlist_variant_ids(
        request.user, [variant.id for variant in variant_list]
    )
    page_obj.object_list = [
        {
            "variant": variant,
            "image": _get_primary_image_for_variant(variant),
            "in_wishlist": variant.id in wishlist_variant_ids,
            "total_sold": variant.total_sold,
        }
        for variant in variant_list
    ]
    user_wishlists = _get_user_wishlists(request.user)
    return render(
        request,
        "user/best_sellers.html",
        {"page_obj": page_obj, "wishlists": user_wishlists},
    )


def get_brands_ajax(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    category = request.GET.get("category")
    subcategory = request.GET.get("subcategory")
    search = request.GET.get("search")

    brand_query = Product.objects.filter(
        is_active=True, approval_status="APPROVED", seller__status="APPROVED"
    )

    if category:
        brand_query = brand_query.filter(subcategory__category__slug=category)
    if subcategory:
        brand_query = brand_query.filter(subcategory__slug=subcategory)
    if search:
        search_query = search.strip()
        brand_query = brand_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )

    brands = (
        brand_query.values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
        .order_by("brand")
    )

    return JsonResponse({"brands": list(brands), "count": len(brands)})


def get_subcategories_ajax(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    category = request.GET.get("category")
    subcategories = get_cached_subcategory_options(category)

    return JsonResponse(
        {"subcategories": list(subcategories), "count": len(subcategories)}
    )

def search_autocomplete(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    products = (
        Product.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query),
            is_active=True,
            approval_status="APPROVED",
            seller__status="APPROVED",
        )
        .values("name", "slug", "brand")
        .distinct()[:5]
    )

    categories = Category.objects.filter(name__icontains=query, is_active=True).values(
        "name", "slug"
    )[:3]

    brands = (
        Product.objects.filter(
            brand__icontains=query,
            is_active=True,
            approval_status="APPROVED",
            seller__status="APPROVED",
        )
        .values_list("brand", flat=True)
        .distinct()[:3]
    )

    suggestions = {
        "products": list(products),
        "categories": list(categories),
        "brands": list(brands),
        "query": query,
    }

    return JsonResponse(suggestions)

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def display_order(request):

    user = request.user

    order_items = (
        OrderItem.objects.filter(order__user=user)
        .exclude(status="CANCELLED")
        .select_related("order", "variant__product", "seller", "seller__user")
        .prefetch_related("variant__images")
        .order_by("-order__ordered_at")
    )

    for item in order_items:
        from django.utils import timezone

        if item.status in ["PENDING", "CONFIRMED"]:
            ship_info = (
                item.estimated_ship_date.date().strftime("%b %d")
                if item.estimated_ship_date
                else "Soon"
            )
            item.shipment_display = f"Ships by {ship_info}"
            item.shipment_class = "text-blue-600 font-semibold"
        elif item.status == "SHIPPED":
            ship_date = (
                item.shipped_at.date().strftime("%b %d") if item.shipped_at else "Today"
            )
            item.shipment_display = f"Shipped on {ship_date}"
            item.shipment_class = "text-green-600 font-semibold"
        else:
            item.shipment_display = None

        # Return eligibility check
        eligibility = _get_return_eligibility(item)
        item.can_return = eligibility["eligible"]
        item.return_expired = eligibility["expired"]

    paginator = Paginator(order_items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "user/orders.html", {"page_obj": page_obj})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def order_cancel(request, order_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.order_status in ["DELIVERED", "SHIPPED", "CANCELLED"]:
        return JsonResponse(
            {"success": False, "message": "This order cannot be cancelled"}, status=400
        )

    with transaction.atomic():
        order.order_status = "CANCELLED"
        order.save()
        for item in order.items.all():
            item.status = "CANCELLED"
            item.save()
            _restock_order_item(item)
    return JsonResponse({"success": True, "message": "Order cancelled successfully"})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def order_item_cancel(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if order_item.status in ["DELIVERED", "SHIPPED", "CANCELLED"]:
        return JsonResponse(
            {"success": False, "message": "This item cannot be cancelled"}, status=400
        )

    with transaction.atomic():
        order_item.status = "CANCELLED"
        order_item.save()
        _restock_order_item(order_item)

    return JsonResponse({"success": True, "message": "Item cancelled successfully"})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def request_return(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    eligibility = _get_return_eligibility(item)
    if not eligibility["eligible"]:
        messages.error(request, eligibility["message"])
        return redirect("user_orders")

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "Return reason is required.")
        return redirect("user_orders")

    images = request.FILES.getlist("images")
    if len(images) > MAX_RETURN_IMAGES:
        messages.error(request, f"You can upload at most {MAX_RETURN_IMAGES} images.")
        return redirect("user_orders")

    for image in images:
        validation_error = _validate_image_file(image, label="Return image")
        if validation_error:
            messages.error(request, validation_error)
            return redirect("user_orders")

    with transaction.atomic():
        return_req = ReturnRequest.objects.create(
            order_item=item, reason=reason, status="PENDING"
        )

        for image in images:
            ReturnRequestImage.objects.create(return_request=return_req, image=image)

        item.status = "RETURN_REQUESTED"
        item.save()

    messages.success(request, "Return requested successfully.")
    return redirect("user_orders")

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def profile_settings(request):
    user = request.user
    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == "POST":
        profile_image = request.FILES.get("profile_image")
        if profile_image:
            validation_error = _validate_image_file(
                profile_image, label="Profile image"
            )
            if validation_error:
                messages.error(request, validation_error)
                return redirect("profile_settings")

        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")
        user.phone_number = request.POST.get("phone_number")
        user.dob = request.POST.get("dob") if request.POST.get("dob") else None
        user.gender = request.POST.get("gender")
        if profile_image:
            user.profile_image = profile_image
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("profile_settings")
    return render(
        request,
        "user/profile.html",
        {"addresses": addresses, "default_address": default_address, "user": user},
    )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user).order_by("-is_default", "-id")
    return render(request, "user/addresses.html", {"addresses": addresses})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def user_address(request):
    if request.method != "POST":
        return redirect("manage_addresses")

    payload = _normalize_address_payload(request)
    required_fields = (
        "full_name",
        "phone_number",
        "pincode",
        "locality",
        "house_info",
        "city",
        "state",
        "country",
        "address_type",
    )
    if any(not payload[field] for field in required_fields):
        messages.error(request, "All address fields are required.")
        return redirect("manage_addresses")

    with transaction.atomic():
        if payload["is_default"]:
            Address.objects.filter(user=request.user).update(is_default=False)
        Address.objects.create(
            user=request.user,
            **payload,
        )
    messages.success(request, "Address added successfully.")
    return redirect("manage_addresses")

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def edit_address(request, id):
    if request.method != "POST":
        return redirect("manage_addresses")

    address = get_object_or_404(Address, id=id, user=request.user)
    payload = _normalize_address_payload(request)
    required_fields = (
        "full_name",
        "phone_number",
        "pincode",
        "locality",
        "house_info",
        "city",
        "state",
        "country",
        "address_type",
    )
    if any(not payload[field] for field in required_fields):
        messages.error(request, "All address fields are required.")
        return redirect("manage_addresses")

    with transaction.atomic():
        if payload["is_default"]:
            Address.objects.filter(user=request.user).update(is_default=False)
        for field, value in payload.items():
            setattr(address, field, value)
        address.save()
    messages.success(request, "Address updated successfully.")
    return redirect("manage_addresses")

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def delete_address(request, id):
    if request.method != "POST":
        messages.error(request, "Invalid address removal request.")
        return redirect("manage_addresses")

    address = get_object_or_404(Address, id=id, user=request.user)
    address.delete()
    messages.success(request, "Address removed successfully.")
    return redirect("manage_addresses")

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def toggle_wishlist(request, variant_id, wishlist_id=None):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    variant = _get_customer_visible_variant_or_404(variant_id)
    user = request.user

    if wishlist_id:
        wishlist = get_object_or_404(Wishlist, id=wishlist_id, user=user)
    else:
        try:
            data = json.loads(request.body)
            w_id = data.get("wishlist_id")
            if w_id:
                wishlist = get_object_or_404(Wishlist, id=w_id, user=user)
            else:
                wishlist, _ = Wishlist.objects.get_or_create(
                    user=user, wishlist_name="My Wishlist"
                )
        except:
            wishlist, _ = Wishlist.objects.get_or_create(
                user=user, wishlist_name="My Wishlist"
            )

    wishlist_item = WishlistItem.objects.filter(
        wishlist=wishlist, variant=variant
    ).first()
    if wishlist_item:
        wishlist_item.delete()
        return JsonResponse(
            {
                "success": True,
                "action": "removed",
                "message": "Removed from wishlist",
                "in_wishlist": False,
            }
        )
    else:
        WishlistItem.objects.create(wishlist=wishlist, variant=variant)
        return JsonResponse(
            {
                "success": True,
                "action": "added",
                "message": f"Added to {wishlist.wishlist_name}",
                "in_wishlist": True,
            }
        )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def wishlist_view(request):
    user = request.user
    wishlist_id = request.GET.get("wishlist_id")
    if wishlist_id:
        wishlist = get_object_or_404(Wishlist, id=wishlist_id, user=user)
    else:
        wishlist = Wishlist.objects.filter(
            user=user, wishlist_name="My Wishlist"
        ).first()
    if not wishlist:
        return render(request, "user/wishlist.html", {"page_obj": None})
    items = (
        WishlistItem.objects.filter(wishlist=wishlist)
        .select_related("variant__product", "variant__product__seller")
        .prefetch_related("variant__images")
        .order_by("-added_at")
    )

    paginator = Paginator(items, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request, "user/wishlist.html", {"page_obj": page_obj, "wishlist": wishlist}
    )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def specific_wishlist_view(request, wishlist_id):
    """
    View specific wishlist by ID
    """
    user = request.user
    wishlist = get_object_or_404(Wishlist, id=wishlist_id, user=user)
    items = (
        WishlistItem.objects.filter(wishlist=wishlist)
        .select_related("variant__product", "variant__product__seller")
        .prefetch_related("variant__images")
        .order_by("-added_at")
    )

    paginator = Paginator(items, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request, "user/wishlist.html", {"page_obj": page_obj, "wishlist": wishlist}
    )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def remove_from_wishlist(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    wishlist_item = get_object_or_404(
        WishlistItem, id=item_id, wishlist__user=request.user
    )
    wishlist_item.delete()
    return JsonResponse({"success": True, "message": "Item removed from wishlist"})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def manage_wishlists(request):
    user = request.user
    wishlists = (
        Wishlist.objects.filter(user=user)
        .annotate(item_count=Count("items"))
        .prefetch_related("items__variant__images")
        .order_by("-created_at")
    )
    return render(request, "user/manage_wishlists.html", {"wishlists": wishlists})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def create_wishlist(request):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    wishlist_name = request.POST.get("wishlist_name", "").strip()
    if not wishlist_name:
        return JsonResponse({"success": False, "message": "Wishlist name is required"})

    if len(wishlist_name) > 100:
        return JsonResponse({"success": False, "message": "Wishlist name too long"})

    if Wishlist.objects.filter(user=request.user, wishlist_name=wishlist_name).exists():
        return JsonResponse(
            {"success": False, "message": "Wishlist with this name already exists"}
        )

    wishlist = Wishlist.objects.create(user=request.user, wishlist_name=wishlist_name)
    return JsonResponse(
        {
            "success": True,
            "message": "Wishlist created successfully",
            "wishlist_id": wishlist.id,
        }
    )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def edit_wishlist(request, wishlist_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    wishlist = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
    wishlist_name = request.POST.get("wishlist_name", "").strip()

    if not wishlist_name:
        return JsonResponse({"success": False, "message": "Wishlist name is required"})

    if len(wishlist_name) > 100:
        return JsonResponse({"success": False, "message": "Wishlist name too long"})

    if (
        Wishlist.objects.filter(user=request.user, wishlist_name=wishlist_name)
        .exclude(id=wishlist_id)
        .exists()
    ):
        return JsonResponse(
            {"success": False, "message": "Wishlist with this name already exists"}
        )

    wishlist.wishlist_name = wishlist_name
    wishlist.save()
    return JsonResponse({"success": True, "message": "Wishlist updated successfully"})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def delete_wishlist(request, wishlist_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    wishlist = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)

    if wishlist.wishlist_name == "My Wishlist":
        return JsonResponse(
            {"success": False, "message": "Cannot delete default wishlist"}
        )

    wishlist.delete()
    return JsonResponse({"success": True, "message": "Wishlist deleted successfully"})

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def move_to_cart(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    wishlist_item = get_object_or_404(
        WishlistItem, id=item_id, wishlist__user=request.user
    )

    variant = wishlist_item.variant

    if not _is_variant_customer_visible(variant):
        return JsonResponse(
            {
                "success": False,
                "message": "This product is no longer available",
            },
            status=400,
        )

    if variant.stock_quantity <= 0:
        return JsonResponse({"success": False, "message": "Product is out of stock"})

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={"quantity": 1, "price_at_time": variant.selling_price},
    )

    if not created:
        if cart_item.quantity + 1 <= variant.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Only {variant.stock_quantity} items available",
                }
            )
    total = sum(item.quantity * item.price_at_time for item in cart.items.all())
    cart.total_amount = total
    cart.save()

    wishlist_item.delete()

    return JsonResponse({"success": True, "message": "Item moved to cart successfully"})


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def toggle_review_helpful(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    review = get_object_or_404(Review, id=review_id)
    user = request.user

    helpful_vote = ReviewHelpful.objects.filter(review=review, user=user).first()

    if helpful_vote:
        helpful_vote.delete()
        review.helpful_count = max(0, review.helpful_count - 1)
        review.save()
        return JsonResponse(
            {
                "success": True,
                "action": "removed",
                "helpful_count": review.helpful_count,
                "message": "Vote removed",
            }
        )
    else:

        ReviewHelpful.objects.create(review=review, user=user)
        review.helpful_count += 1
        review.save()
        return JsonResponse(
            {
                "success": True,
                "action": "added",
                "helpful_count": review.helpful_count,
                "message": "Marked as helpful",
            }
        )

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _send_order_confirmation(order):
    """
    Helper to send unified notifications (In-App, Email, WhatsApp) for order confirmation.
    """
    user = order.user

    try:
        url = reverse("order_success", args=[order.id])
        create_notification(
            user=user,
            type="order_success",
            title="Order Confirmed!",
            message=f"Your order {order.order_number} has been successfully placed.",
            redirect_url=url,
        )
    except Exception as e:
        logger.error(f"In-App Notification Failed: {e}")

    try:
        send_mail(
            subject=f"Order Confirmed: {order.order_number}",
            message=f"Hi {user.first_name},\n\nYour order {order.order_number} has been confirmed successfully.\nTotal Amount: ₹{order.total_amount}\n\nThank you for shopping with EasyBuy!",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Email Notification Failed: {e}")

    if getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False):
        try:
            notifier = WhatsAppNotifier()
            logger.info(
                f"Sending WhatsApp to {order.shipping_phone} for Order {order.order_number}"
            )
            notifier.send_order_confirmation(order)
        except Exception as e:
            logger.error(f"WhatsApp Notification Failed: {e}")

def _money(value):
    return DzDecimal(value or 0).quantize(MONEY_PRECISION)

def _get_checkout_coupon(raw_code):
    raw_code = (raw_code or "").strip().upper()
    if not raw_code:
        return None
    return (
        Coupon.objects.select_related(
            "seller",
            "category",
            "subcategory",
            "product__seller",
            "product__subcategory__category",
        )
        .filter(code=raw_code)
        .first()
    )

def _remove_checkout_coupon(request):
    request.session.pop(CHECKOUT_PROMO_SESSION_KEY, None)

def _build_checkout_summary(
    request,
    *,
    buy_now_variant_id=None,
    buy_now_quantity=1,
    promo_code=None,
):
    user = request.user
    addresses = user.addresses.all().order_by("-is_default", "-id")

    cart = None
    variant = None
    quantity = max(int(buy_now_quantity or 1), 1)
    line_items = []

    if buy_now_variant_id:
        variant = (
            _customer_visible_variants_queryset()
            .select_related("product__subcategory__category")
            .filter(id=buy_now_variant_id)
            .first()
        )
        if variant is None:
            raise ValueError("This product is no longer available")
        if variant.stock_quantity < quantity:
            raise ValueError("Insufficient stock")
        line_total = _money(variant.selling_price * quantity)
        line_items.append(
            {
                "variant": variant,
                "product": variant.product,
                "quantity": quantity,
                "unit_price": _money(variant.selling_price),
                "line_total": line_total,
            }
        )
    else:
        cart = (
            Cart.objects.filter(user=user)
            .prefetch_related("items__variant__product__subcategory__category")
            .first()
        )
        if not cart or not cart.items.exists():
            raise ValueError("Your cart is empty")
        for item in cart.items.all():
            if not _is_variant_customer_visible(item.variant):
                raise ValueError(f"{item.variant.product.name} is no longer available")
            if item.variant.stock_quantity < item.quantity:
                raise ValueError(f"Insufficient stock for {item.variant.product.name}")
            line_items.append(
                {
                    "variant": item.variant,
                    "product": item.variant.product,
                    "quantity": item.quantity,
                    "unit_price": _money(item.price_at_time),
                    "line_total": _money(item.quantity * item.price_at_time),
                }
            )

    subtotal = _money(sum(item["line_total"] for item in line_items))
    shipping = _money("99") if subtotal < DzDecimal("999") else _money("0")

    promo_code = (promo_code or "").strip().upper()
    applied_coupon = None
    promo_error = ""
    discount_amount = _money("0")

    if promo_code:
        coupon = _get_checkout_coupon(promo_code)
        if not coupon:
            promo_error = "Promo code not found."
        elif not coupon.is_currently_valid():
            promo_error = "This promo code is inactive or expired."
        elif subtotal < _money(coupon.min_order_amount):
            promo_error = f"This promo code requires a minimum subtotal of ₹{coupon.min_order_amount:.2f}."
        else:
            eligible_subtotal = _money(
                sum(
                    item["line_total"]
                    for item in line_items
                    if coupon.matches_product(item["product"])
                )
            )
            if eligible_subtotal <= 0:
                promo_error = "This promo code does not apply to the selected items."
            else:
                discount_amount = _money(coupon.calculate_discount(eligible_subtotal))
                if discount_amount <= 0:
                    promo_error = "This promo code does not reduce the current total."
                else:
                    applied_coupon = coupon
                    promo_code = coupon.code

    discounted_subtotal = _money(subtotal - discount_amount)
    tax = _money(discounted_subtotal * DzDecimal("0.18"))
    grand_total = _money(discounted_subtotal + shipping + tax)

    return {
        "cart": cart,
        "variant": variant,
        "quantity": quantity,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount_amount": discount_amount,
        "tax_amount": tax,
        "grand_total": grand_total,
        "single_product": bool(buy_now_variant_id),
        "promo_code": promo_code if applied_coupon else "",
        "promo_message": (
            f"{applied_coupon.code} applied to {applied_coupon.target_name}."
            if applied_coupon
            else ""
        ),
        "promo_error": promo_error,
        "applied_coupon": applied_coupon,
    }


def _serialize_checkout_totals(summary):
    return {
        "subtotal": f"{summary['subtotal']:.2f}",
        "shipping": f"{summary['shipping']:.2f}",
        "discount_amount": f"{summary['discount_amount']:.2f}",
        "tax_amount": f"{summary['tax_amount']:.2f}",
        "grand_total": f"{summary['grand_total']:.2f}",
        "promo_code": summary["promo_code"],
        "promo_message": summary["promo_message"],
    }

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def checkout(request):
    buy_now_variant_id = request.session.get("buy_now_variant_id")
    quantity = request.session.get("buy_now_quantity", 1)
    promo_code = request.session.get(CHECKOUT_PROMO_SESSION_KEY, "")

    try:
        context = _build_checkout_summary(
            request,
            buy_now_variant_id=buy_now_variant_id,
            buy_now_quantity=quantity,
            promo_code=promo_code,
        )
    except ValueError as exc:
        _remove_checkout_coupon(request)
        return render(request, "user/checkout.html", {"error": str(exc)})

    if context["promo_error"]:
        _remove_checkout_coupon(request)

    return render(request, "user/checkout.html", context)

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def apply_promo_code(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid data"}, status=400)

    code = (data.get("promo_code") or "").strip().upper()
    if not code:
        return JsonResponse({"error": "Enter a promo code."}, status=400)

    try:
        summary = _build_checkout_summary(
            request,
            buy_now_variant_id=request.session.get("buy_now_variant_id"),
            buy_now_quantity=request.session.get("buy_now_quantity", 1),
            promo_code=code,
        )
    except ValueError as exc:
        _remove_checkout_coupon(request)
        return JsonResponse({"error": str(exc)}, status=400)

    if summary["promo_error"] or not summary["promo_code"]:
        _remove_checkout_coupon(request)
        return JsonResponse({"error": summary["promo_error"]}, status=400)

    request.session[CHECKOUT_PROMO_SESSION_KEY] = summary["promo_code"]
    return JsonResponse(
        {
            "success": True,
            "totals": _serialize_checkout_totals(summary),
        }
    )

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def remove_promo_code(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    _remove_checkout_coupon(request)

    try:
        summary = _build_checkout_summary(
            request,
            buy_now_variant_id=request.session.get("buy_now_variant_id"),
            buy_now_quantity=request.session.get("buy_now_quantity", 1),
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "success": True,
            "totals": _serialize_checkout_totals(summary),
        }
    )


@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        address_id = data.get("selected_address_id")
        payment_method = (data.get("payment_method") or "ONLINE").upper()
        promo_code = (data.get("promo_code") or "").strip().upper()
    except json.JSONDecodeError:
        logger.error("Invalid JSON in create_razorpay_order request")
        return JsonResponse({"error": "Invalid data"}, status=400)

    user = request.user

    try:
        address = get_object_or_404(Address, id=address_id, user=user)
    except Http404:
        logger.warning(f"Invalid address ID {address_id} for user {user.id}")
        return JsonResponse({"error": "Invalid delivery address"}, status=400)

    if payment_method not in {"ONLINE", "COD"}:
        return JsonResponse({"error": "Invalid payment method"}, status=400)

    buy_now_variant_id = data.get("buy_now_variant_id")

    try:
        buy_now_quantity = int(data.get("buy_now_quantity", 1))
    except (ValueError, TypeError):
        logger.error("Invalid quantity in create_razorpay_order")
        return JsonResponse({"error": "Invalid quantity"}, status=400)

    try:
        summary = _build_checkout_summary(
            request,
            buy_now_variant_id=buy_now_variant_id,
            buy_now_quantity=buy_now_quantity,
            promo_code=promo_code,
        )
        if promo_code and summary["promo_error"]:
            return JsonResponse({"error": summary["promo_error"]}, status=400)

        cart = summary["cart"]
        variant = summary["variant"]
        grand_total = summary["grand_total"]
        applied_promo_code = summary["promo_code"]
        discount_amount = summary["discount_amount"]

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                order_number=f"EB{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6]}",
                total_amount=grand_total,
                discount_amount=discount_amount,
                promo_code=applied_promo_code,
                payment_status="PENDING",
                order_status="PENDING",
                shipping_name=address.full_name,
                shipping_phone=address.phone_number,
                shipping_address=f"{address.house_info}, {address.city}, {address.state}",
                payment_method=payment_method,
            )

            if buy_now_variant_id:
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    seller=variant.product.seller,
                    quantity=buy_now_quantity,
                    price_at_purchase=variant.selling_price,
                )
            else:
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        seller=item.variant.product.seller,
                        quantity=item.quantity,
                        price_at_purchase=item.price_at_time,
                    )

            logger.info(f"Order created: {order.order_number} for user {user.id}")

            if payment_method == "COD":
                request.session["pending_order_id"] = order.id
                return JsonResponse(
                    {
                        "cod_ready": True,
                        "internal_order_id": order.id,
                    }
                )

            amount_paise = int(order.total_amount * 100)
            logger.info(
                "Creating Razorpay order for %s: amount=%s",
                order.order_number,
                order.total_amount,
            )
            try:
                razorpay_order = client.order.create(
                    {
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": order.order_number,
                    }
                )

                if not razorpay_order or "id" not in razorpay_order:
                    logger.error(
                        f"Razorpay API returned invalid response: {razorpay_order}"
                    )
                    raise RazorpayOrderError(
                        {
                            "error": "Payment gateway error. Razorpay order creation failed"
                        },
                        500,
                    )

                order.razorpay_order_id = razorpay_order["id"]
                order.save(update_fields=["razorpay_order_id"])

                logger.info(
                    "Razorpay order created: %s for %s",
                    razorpay_order["id"],
                    order.order_number,
                )

                request.session["pending_order_id"] = order.id
                if applied_promo_code:
                    request.session[CHECKOUT_PROMO_SESSION_KEY] = applied_promo_code

                # Validate prefill data
                prefill_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                if not prefill_name:
                    prefill_name = user.username

                return JsonResponse(
                    {
                        "key": settings.RAZORPAY_KEY_ID,
                        "amount": amount_paise,
                        "order_id": razorpay_order["id"],
                        "internal_order_id": order.id,
                        "prefill": {
                            "name": prefill_name,
                            "email": user.email or "",
                            "contact": address.phone_number,
                        },
                    }
                )

            except (
                razorpay.errors.BadRequestError,
                razorpay.errors.GatewayError,
                razorpay.errors.ServerError,
            ) as e:
                logger.error(f"Razorpay API Error: {str(e)}", exc_info=True)
                raise RazorpayOrderError(
                    {
                        "error": f"Payment gateway error: {str(e)}",
                        "details": "Unable to connect to Razorpay. Please try again.",
                    },
                    502,
                ) from e
            except RazorpayOrderError:
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error creating Razorpay order: {str(e)}", exc_info=True
                )
                raise RazorpayOrderError(
                    {"error": "Unexpected error. Please contact support."},
                    500,
                ) from e

    except RazorpayOrderError as e:
        return JsonResponse(e.payload, status=e.status_code)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in create_razorpay_order: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "An error occurred while processing your order"}, status=500
        )


@login_required
def log_razorpay_failure(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid data"}, status=400)

    razorpay_order_id = str(data.get("razorpay_order_id", "")).strip()
    razorpay_payment_id = str(data.get("razorpay_payment_id", "")).strip()
    error_data = data.get("error") or {}

    if not razorpay_order_id:
        return JsonResponse({"error": "Missing razorpay_order_id"}, status=400)

    order = Order.objects.filter(
        razorpay_order_id=razorpay_order_id,
        user=request.user,
    ).first()
    if not order:
        return JsonResponse({"error": "Order not found"}, status=404)

    order.payment_status = "FAILED"
    order.order_status = "CANCELLED"
    if razorpay_payment_id:
        order.razorpay_payment_id = razorpay_payment_id
    order.save(update_fields=["payment_status", "order_status", "razorpay_payment_id"])

    OrderItem.objects.filter(order=order).update(status="CANCELLED")

    PaymentTransaction.objects.get_or_create(
        order=order,
        transaction_id=razorpay_payment_id or f"failed-{timezone.now().timestamp()}",
        defaults={
            "payment_gateway": "Razorpay",
            "amount": order.total_amount,
            "status": "FAILED",
            "gateway_response": (
                error_data if isinstance(error_data, dict) else {"raw": error_data}
            ),
        },
    )

    logger.warning(
        "Razorpay payment failed for order %s: %s",
        order.order_number,
        error_data,
    )
    return JsonResponse({"success": True})


@login_required
def verify_razorpay_payment(request):
    """Verify Razorpay payment signature and confirm order"""
    if request.method != "POST":
        messages.error(request, "Invalid payment verification request.")
        return redirect("checkout")

    try:
        razorpay_order_id = request.POST.get("razorpay_order_id", "").strip()
        razorpay_payment_id = request.POST.get("razorpay_payment_id", "").strip()
        razorpay_signature = request.POST.get("razorpay_signature", "").strip()

        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            logger.warning(f"Missing parameters in verify_razorpay_payment")
            messages.error(request, "Payment verification failed: Missing parameters")
            return redirect("checkout")

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }

        logger.info(
            f"Verifying Razorpay payment: order_id={razorpay_order_id}, payment_id={razorpay_payment_id}"
        )

        try:
            order = Order.objects.get(
                razorpay_order_id=razorpay_order_id, user=request.user
            )
        except Order.DoesNotExist:
            logger.error(f"Order not found for razorpay_order_id: {razorpay_order_id}")
            messages.error(request, "Payment verification failed: Order not found")
            return redirect("checkout")

        order.razorpay_payment_id = razorpay_payment_id
        order.save()

        try:
            client.utility.verify_payment_signature(params_dict)
            logger.info(
                f"Signature verified successfully for order {order.order_number}"
            )
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(
                f"Signature verification FAILED for order {order.order_number}: {str(e)}"
            )
            order.payment_status = "FAILED"
            order.order_status = "CANCELLED"
            order.save(update_fields=["payment_status", "order_status"])
            OrderItem.objects.filter(order=order).update(status="CANCELLED")
            messages.error(request, "Payment verification failed: Invalid signature")
            return redirect("user_orders")
        except Exception as e:
            logger.error(
                f"Unexpected error during signature verification: {str(e)}",
                exc_info=True,
            )
            order.payment_status = "FAILED"
            order.order_status = "CANCELLED"
            order.save(update_fields=["payment_status", "order_status"])
            OrderItem.objects.filter(order=order).update(status="CANCELLED")
            messages.error(
                request, "Payment verification error. Please contact support."
            )
            return redirect("user_orders")

        clear_cart = not request.session.get("buy_now_variant_id")

        try:
            order, was_confirmed = _finalize_online_order(
                order,
                razorpay_payment_id,
                params_dict,
                clear_cart=clear_cart,
            )
            if was_confirmed:
                logger.info(
                    f"Payment verified and order confirmed: {order.order_number}"
                )
            else:
                logger.info(
                    "Order %s already verified; returning success page",
                    order.order_number,
                )

            request.session.pop("buy_now_variant_id", None)
            request.session.pop("buy_now_quantity", None)
            request.session.pop("pending_order_id", None)
            _remove_checkout_coupon(request)
            return redirect("order_success", order_id=order.id)

        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}", exc_info=True)
            order.payment_status = "PARTIAL"
            order.save()
            messages.error(
                request,
                "Payment received but order processing failed. Support team notified.",
            )
            return redirect("user_orders")

    except Exception as e:
        logger.error(
            f"Unexpected error in verify_razorpay_payment: {str(e)}", exc_info=True
        )
        messages.error(request, "An unexpected error occurred. Please contact support.")
        return redirect("checkout")


@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        logger.error("Razorpay webhook called without webhook secret configured.")
        return JsonResponse({"error": "Webhook not configured"}, status=503)

    signature = request.headers.get("X-Razorpay-Signature", "").strip()
    if not signature:
        return JsonResponse({"error": "Missing webhook signature"}, status=400)

    body = request.body.decode("utf-8")
    try:
        client.utility.verify_webhook_signature(body, signature, webhook_secret)
    except razorpay.errors.SignatureVerificationError:
        logger.warning("Invalid Razorpay webhook signature.")
        return JsonResponse({"error": "Invalid signature"}, status=400)

    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    event = str(payload.get("event", "")).strip()
    if event not in {"payment.captured", "order.paid"}:
        return JsonResponse({"status": "ignored", "event": event}, status=200)

    razorpay_order_id, razorpay_payment_id, payment_entity = (
        _extract_razorpay_payment_details(payload)
    )
    if not razorpay_order_id or not razorpay_payment_id:
        logger.warning("Webhook missing payment identifiers for event %s", event)
        return JsonResponse({"error": "Missing payment identifiers"}, status=400)

    order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not order:
        logger.warning(
            "Webhook received for unknown Razorpay order %s", razorpay_order_id
        )
        return JsonResponse({"status": "missing_order"}, status=202)

    try:
        order, was_confirmed = _finalize_online_order(
            order,
            razorpay_payment_id,
            {
                "event": event,
                "payment": payment_entity,
            },
            clear_cart=False,
        )
    except Exception:
        logger.exception(
            "Webhook failed to finalize order %s for Razorpay order %s",
            order.order_number,
            razorpay_order_id,
        )
        if order.payment_status != "PAID":
            order.payment_status = "PARTIAL"
            order.save(update_fields=["payment_status"])
        return JsonResponse({"error": "Order reconciliation failed"}, status=500)

    status = "confirmed" if was_confirmed else "already_confirmed"
    return JsonResponse({"status": status, "order_id": order.id}, status=200)


@login_required
def process_cod_order(request):
    if request.method != "POST":
        return redirect("checkout")

    order_id = request.session.get("pending_order_id")
    if not order_id:
        return redirect("checkout")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .prefetch_related("items__variant")
            .get(pk=order.pk)
        )
        if order.order_status == "CONFIRMED":
            return redirect("order_success", order_id=order.id)

        for item in order.items.all():
            ProductVariant.objects.select_for_update().filter(
                pk=item.variant_id
            ).first()
            variant = ProductVariant.objects.get(pk=item.variant_id)
            if not item.stock_deducted and variant.stock_quantity < item.quantity:
                messages.error(
                    request, f"Insufficient stock for {item.variant.product.name}"
                )
                return redirect("checkout")

        for item in order.items.all():
            if not _deduct_order_item_stock(item):
                messages.error(
                    request, f"Insufficient stock for {item.variant.product.name}"
                )
                return redirect("checkout")

        order.payment_method = "COD"
        order.payment_status = "PENDING"
        order.order_status = "CONFIRMED"
        order.save()

        if not request.session.get("buy_now_variant_id"):
            Cart.objects.filter(user=request.user).delete()

        _send_order_confirmation(order)

        request.session.pop("pending_order_id", None)
        request.session.pop("buy_now_variant_id", None)
        request.session.pop("buy_now_quantity", None)
        _remove_checkout_coupon(request)

    return redirect("order_success", order_id=order.id)


@login_required
def buy_now(request, variant_id):
    variant = _get_customer_visible_variant_or_404(variant_id)
    if variant.stock_quantity <= 0:
        messages.error(request, "Out of stock")
        return redirect("product_detail_user", slug=variant.product.slug)

    request.session["buy_now_variant_id"] = variant.id
    request.session["buy_now_quantity"] = 1
    return redirect("checkout")


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(
        request,
        "user/order_success.html",
        {"order": order, "payment_method": order.payment_method},
    )


@login_required
def notification_settings(request):
    pref, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        pref.email_order_updates = request.POST.get("email_order_updates") == "on"
        pref.whatsapp_order_updates = request.POST.get("whatsapp_order_updates") == "on"
        pref.email_promotions = request.POST.get("email_promotions") == "on"
        pref.whatsapp_promotions = request.POST.get("whatsapp_promotions") == "on"
        pref.save()

        messages.success(request, "Notification preferences updated successfully!")
        return redirect("notification_settings")

    return render(request, "user/notification_preferences.html", {"pref": pref})


@login_required
def all_notifications(request):
    filter_type = request.GET.get("filter", "all")
    notifications_qs = Notification.objects.filter(user=request.user)

    if filter_type == "unread":
        notifications_qs = notifications_qs.filter(is_read=False)

    notifications_list = notifications_qs.order_by("-created_at")
    paginator = Paginator(notifications_list, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "user/notifications.html",
        {"page_obj": page_obj, "current_filter": filter_type},
    )


@login_required
def payment_methods(request):
    if request.method == "POST":
        card_holder_name = request.POST.get("card_holder_name")
        card_number = request.POST.get("card_number")
        expiry = request.POST.get("expiry") 

        if card_holder_name and card_number and expiry:
            try:
                if "/" not in expiry:
                    raise ValueError("Invalid expiry format. Use MM/YY")
                month, year = expiry.split("/")

                brand = "Visa" if card_number.startswith("4") else "Mastercard"
                if card_number.startswith("3"):
                    brand = "Amex"

                SavedCard.objects.create(
                    user=request.user,
                    card_holder_name=card_holder_name,
                    card_number=card_number[-4:], 
                    expiry_month=month,
                    expiry_year=year,
                    card_brand=brand,
                )
                messages.success(request, "Payment method added successfully.")
            except Exception as e:
                messages.error(request, f"Failed to add card: {e}")
        else:
            messages.error(request, "All fields are required.")
        return redirect("payment_methods")

    cards = SavedCard.objects.filter(user=request.user).order_by(
        "-is_default", "-created_at"
    )
    return render(request, "user/payment_methods.html", {"cards": cards})


@login_required
def delete_saved_card(request, card_id):
    if request.method == "POST":
        card = get_object_or_404(SavedCard, id=card_id, user=request.user)
        card.delete()
        messages.success(request, "Payment method removed successfully.")
    return redirect("payment_methods")


@login_required
def mark_notification_read(request, notification_id):
    if request.method == "POST":
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user
        )
        notification.is_read = True
        notification.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            unread_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
            return JsonResponse({"success": True, "unread_count": unread_count})

        messages.success(request, "Notification marked as read")
    return redirect("all_notifications")


@login_required
def delete_notification(request, notification_id):
    if request.method == "POST":
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user
        )
        notification.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            unread_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
            return JsonResponse({"success": True, "unread_count": unread_count})

        messages.success(request, "Notification deleted")
    return redirect("all_notifications")


@login_required
def mark_all_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        invalidate_user_header_cache(request.user.id)
        messages.success(request, "All notifications marked as read")
    return redirect("all_notifications")
