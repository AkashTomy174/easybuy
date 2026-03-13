from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from easybuy.core.decorators import role_required
from easybuy.seller.models import Product, ProductVariant, ProductImage
from .models import Cart, CartItem, Order, OrderItem, Review, Wishlist, WishlistItem, ReviewImage, ReviewVideo, ReviewHelpful
from easybuy.core.models import SubCategory, Category, Address
from easybuy.core.whatsapp_utils import whatsapp_notifier
import json
from django.http import Http404
from django.db.models import Q, Avg
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from django.core.paginator import Paginator
import random
import string
from django.db.models import Sum


def home_view(request):
    if request.user.is_authenticated:
        if request.user.role == "ADMIN":
            return redirect("admin_dashboard")
        elif request.user.role == "SELLER":
            return redirect("seller_dashboard")

    categories = Category.objects.filter(is_active=True)
    variants = (
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED"
        )
        .select_related("product", "product__seller")
        .prefetch_related("images")
        .order_by("-id")[:8]
    )
    
    # Check wishlist status for authenticated users
    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        variant_ids = [v.id for v in variants]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in variants:
        primary_image = None
        for img in variant.images.filter(is_primary=True):
            if img.image:
                primary_image = img
                break
        if not primary_image:
            for img in variant.images.all():
                if img.image:
                    primary_image = img
                    break
        product_data.append(
            {
                "variant": variant,
                "image": primary_image,
                "in_wishlist": variant.id in wishlist_variant_ids
            }
        )
    return render(
        request,
        "core/home.html",
        {"categories": categories, "product_data": product_data},
    )


def all_categories(request):
    categories = Category.objects.filter(is_active=True)
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

    variants = ProductVariant.objects.filter(
        product__is_active=True,
        product__approval_status="APPROVED",
        product__seller__status="APPROVED",
    ).select_related(
        "product",
        "product__seller",
        "product__subcategory",
        "product__subcategory__category",
    )

    # Base query for brands - start with all approved products
    brand_query = Product.objects.filter(
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED"
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
            product_ids = Product.objects.filter(
                is_active=True,
                approval_status="APPROVED",
                seller__status="APPROVED"
            ).annotate(avg_rating=Avg('reviews__rating')).filter(
                avg_rating__gte=min_rating
            ).values_list('id', flat=True)
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
            avg_rating=Avg('product__reviews__rating')
        ).order_by('-avg_rating', '-id')
    elif sort == "most_popular":
        # Sort by total sales
        variants = variants.annotate(
            total_sold=Sum('orderitem__quantity')
        ).order_by('-total_sold', '-id')
    else:
        variants = variants.order_by("-id")

    # Get brands based on current filters (category/subcategory/search)
    all_brands = (
        brand_query
        .values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
    )

    categories = Category.objects.filter(is_active=True)
    subcategories = SubCategory.objects.filter(is_active=True)

    variant_list = list(variants)
    variant_ids = [v.id for v in variant_list]
    primary_images = {}
    for img in ProductImage.objects.filter(variant_id__in=variant_ids, is_primary=True):
        if img.image:
            primary_images[img.variant_id] = img
    
    # Fallback to any image if no primary image
    for img in ProductImage.objects.filter(variant_id__in=variant_ids).exclude(variant_id__in=primary_images.keys()):
        if img.image and img.variant_id not in primary_images:
            primary_images[img.variant_id] = img

    # Check wishlist status for authenticated users
    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in variant_list:
        product_data.append(
            {
                "variant": variant,
                "image": primary_images.get(variant.id),
                "in_wishlist": variant.id in wishlist_variant_ids
            }
        )

    paginator = Paginator(product_data, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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
    }
    return render(request, "user/all_products.html", context)


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def add_reviews(request, variant_id):

    variant = get_object_or_404(ProductVariant.objects.select_related("product"), id=variant_id)

    product = variant.product
    user = request.user

    has_purchased = OrderItem.objects.filter(
        order__user=user, variant__product=product, order__order_status="DELIVERED"
    ).exists()

    if not has_purchased:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'You can only review products you have purchased and received.'
            })
        messages.error(
            request, "You can only review products you have purchased and received."
        )
        return redirect("product_detail_user", slug=product.slug)

    if Review.objects.filter(user=user, product=product).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'You have already reviewed this product.'
            })
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
            images = request.FILES.getlist('images')
            if len(images) > 5:
                messages.warning(request, "Maximum 5 images allowed. Only first 5 were uploaded.")
                images = images[:5]
            
            for image in images:
                if image.size > 5 * 1024 * 1024:  # 5MB limit
                    messages.warning(request, f"Image {image.name} exceeds 5MB and was skipped.")
                    continue
                ReviewImage.objects.create(review=review, image=image)

            # Handle video uploads
            videos = request.FILES.getlist('videos')
            if len(videos) > 2:
                messages.warning(request, "Maximum 2 videos allowed. Only first 2 were uploaded.")
                videos = videos[:2]
            
            for video in videos:
                if video.size > 50 * 1024 * 1024:  # 50MB limit
                    messages.warning(request, f"Video {video.name} exceeds 50MB and was skipped.")
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
        return JsonResponse({
            "has_purchased": False,
            "has_reviewed": False,
            "can_review": False,
            "message": "Please login to review"
        })
    
    if request.user.role != "CUSTOMER":
        return JsonResponse({
            "has_purchased": False,
            "has_reviewed": False,
            "can_review": False,
            "message": "Only customers can review products"
        })
    
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), id=variant_id)
    product = variant.product
    user = request.user
    has_purchased = OrderItem.objects.filter(
        order__user=user, variant__product=product, order__order_status="DELIVERED"
    ).exists()
    has_reviewed = Review.objects.filter(user=user, product=product).exists()
    return JsonResponse({
        "has_purchased": has_purchased,
        "has_reviewed": has_reviewed,
        "can_review": has_purchased and not has_reviewed
    })


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def reviews(request, variant_id):

    user = request.user

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product").prefetch_related("images"),
        id=variant_id,
    )

    sort_by = request.GET.get('sort', 'recent')

    reviews_qs = (
        Review.objects.select_related("user")
        .prefetch_related("images", "videos")
        .filter(product=variant.product)
    )

    # Sorting
    if sort_by == 'helpful':
        reviews_qs = reviews_qs.order_by("-helpful_count", "-created_at")
    elif sort_by == 'rating_high':
        reviews_qs = reviews_qs.order_by("-rating", "-created_at")
    elif sort_by == 'rating_low':
        reviews_qs = reviews_qs.order_by("rating", "-created_at")
    else:  # recent
        reviews_qs = reviews_qs.order_by("-created_at")

    # Optimize verified purchase check
    review_user_ids = list(reviews_qs.values_list('user_id', flat=True))
    verified_users = set(
        OrderItem.objects.filter(
            order__user_id__in=review_user_ids,
            variant__product=variant.product,
            order__order_status="DELIVERED"
        ).values_list('order__user_id', flat=True).distinct()
    )

    # Check if current user voted helpful
    user_helpful_votes = set(
        ReviewHelpful.objects.filter(
            user=user,
            review__in=reviews_qs
        ).values_list('review_id', flat=True)
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
    return JsonResponse({"success": True, "redirect_url": f"/user/products/{product_slug}/"})


def new_arrival(request):
    variants = (
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related("product", "product__seller")
        .prefetch_related("images")
        .order_by("-id")
    )

    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        variant_ids = [v.id for v in variants]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in variants:
        primary_image = None
        for img in variant.images.filter(is_primary=True):
            if img.image:
                primary_image = img
                break
        if not primary_image:
            for img in variant.images.all():
                if img.image:
                    primary_image = img
                    break
        product_data.append(
            {
                "variant": variant,
                "image": primary_image,
                "in_wishlist": variant.id in wishlist_variant_ids
            }
        )

    paginator = Paginator(product_data, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "user/new_arrivals.html", {"page_obj": page_obj})


def category_products(request, slug=None, id=None):
    if slug:
        categories = get_object_or_404(Category, slug=slug, is_active=True)
    elif id:
        categories = get_object_or_404(Category, id=id, is_active=True)
    else:
        from django.http import Http404

        raise Http404("Category not found")

    subcategory = SubCategory.objects.filter(category=categories, is_active=True)
    variants = ProductVariant.objects.filter(
        product__subcategory__category=categories,
        product__is_active=True,
        product__approval_status="APPROVED",
        product__seller__status="APPROVED",
    ).select_related("product", "product__seller").prefetch_related("images")

    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        variant_ids = [v.id for v in variants]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in variants:
        primary_image = None
        for img in variant.images.filter(is_primary=True):
            if img.image:
                primary_image = img
                break
        if not primary_image:
            for img in variant.images.all():
                if img.image:
                    primary_image = img
                    break
        product_data.append(
            {
                "variant": variant,
                "image": primary_image,
                "in_wishlist": variant.id in wishlist_variant_ids
            }
        )

    paginator = Paginator(product_data, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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
    variants = ProductVariant.objects.filter(
        product__subcategory=current_sub,
        product__is_active=True,
        product__approval_status="APPROVED",
        product__seller__status="APPROVED",
    ).select_related("product", "product__seller").prefetch_related("images")

    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        variant_ids = [v.id for v in variants]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in variants:
        primary_image = None
        for img in variant.images.filter(is_primary=True):
            if img.image:
                primary_image = img
                break
        if not primary_image:
            for img in variant.images.all():
                if img.image:
                    primary_image = img
                    break
        product_data.append(
            {
                "variant": variant,
                "image": primary_image,
                "in_wishlist": variant.id in wishlist_variant_ids
            }
        )

    paginator = Paginator(product_data, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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
            .prefetch_related("variants__images")
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
            .prefetch_related("variants__images")
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
            subcategory=product.subcategory,
            is_active=True,
            approval_status="APPROVED",
            seller__status="APPROVED",
        )
        .exclude(slug=product.slug)[:4]
    )

    reviews = Review.objects.select_related('user').prefetch_related('images', 'videos').filter(product=product).order_by("-created_at")[:5]
    all_reviews = Review.objects.filter(product=product)
    avg_rating = all_reviews.aggregate(Avg("rating"))["rating__avg"] or 0
    total_reviews = all_reviews.count()
    
    # Calculate rating breakdown
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in all_reviews:
        rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1
    
    # Calculate percentages
    rating_breakdown = []
    for rating in [5, 4, 3, 2, 1]:
        count = rating_counts.get(rating, 0)
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_breakdown.append({
            'rating': rating,
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    existing_review = None

    wishlist_variant_ids = set()
    user_helpful_votes = set()
    if request.user.is_authenticated:
        existing_review = Review.objects.filter(
            user=request.user, product=product
        ).first()

        variant_ids = [v.id for v in product.variants.all()]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

        # Optimize verified purchase check
        review_user_ids = [r.user_id for r in reviews]
        verified_users = set(
            OrderItem.objects.filter(
                order__user_id__in=review_user_ids,
                variant__product=product,
                order__order_status="DELIVERED"
            ).values_list('order__user_id', flat=True).distinct()
        )
        
        # Check helpful votes
        user_helpful_votes = set(
            ReviewHelpful.objects.filter(
                user=request.user,
                review__in=reviews
            ).values_list('review_id', flat=True)
        )
        
        for review in reviews:
            review.is_verified_purchase = review.user_id in verified_users
            review.user_voted_helpful = review.id in user_helpful_votes

    context = {
        "product": product,
        "related_products": related_products,
        "reviews": reviews,
        "avg_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews,
        "rating_breakdown": rating_breakdown,
        "existing_review": existing_review,
        "wishlist_variant_ids": list(wishlist_variant_ids),
    }
    return render(
        request,
        "user/product_details.html",
        context,
    )


@login_required
@role_required(allowed_roles=["SELLER", "CUSTOMER"])
def addtocart(request, id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    variant = get_object_or_404(ProductVariant, id=id)

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


def filtering(request):
    products = (
        Product.objects.filter(
            is_active=True,
        )
        .select_related("subcategory__category")
        .prefetch_related("variants__images")
    )
    icategory = request.GET.get("category")
    isubCategory = request.GET.get("subcategory")
    ibrand = request.GET.getlist("brand")
    min_price = request.GET.get("min")
    max_price = request.GET.get("max")
    iprod = request.GET.get("q") or request.GET.get("product")
    sort = request.GET.get("sort", "newest")


    brand_query = Product.objects.filter(is_active=True)
    if icategory:
        products = products.filter(subcategory__category__slug=icategory)
        brand_query = brand_query.filter(subcategory__category__slug=icategory)
    if isubCategory:
        products = products.filter(subcategory__slug=isubCategory)
        brand_query = brand_query.filter(subcategory__slug=isubCategory)

    if ibrand:
        products = products.filter(brand__in=ibrand)

    if iprod:
        search_query = iprod.strip()
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )
        brand_query = brand_query.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )

    all_brands = (
        brand_query
        .values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
    )

    categories = Category.objects.filter(is_active=True)
    subcategories = SubCategory.objects.filter(is_active=True)

    if min_price:
        min_price = float(min_price)
        products = products.filter(variants__selling_price__gte=min_price).distinct()

    if max_price:
        max_price = float(max_price)
        products = products.filter(variants__selling_price__lte=max_price).distinct()
    if sort == "price_low":
        products = products.order_by("variants__selling_price")
    elif sort == "price_high":
        products = products.order_by("-variants__selling_price")
    elif sort == "name_asc":
        products = products.order_by("name")
    elif sort == "name_desc":
        products = products.order_by("-name")
    else:
        products = products.order_by("-created_at")
    product_data = []
    for product in products:
        lowest_variant = product.variants.all().order_by("selling_price").first()
        primary_image = None
        if product.variants.all().first():
            first_variant = product.variants.all().first()
            for img in first_variant.images.filter(is_primary=True):
                if img.image:
                    primary_image = img
                    break
            if not primary_image:
                for img in first_variant.images.all():
                    if img.image:
                        primary_image = img
                        break

        product_data.append(
            {
                "product": product,
                "lowest_price": lowest_variant.selling_price if lowest_variant else 0,
                "mrp": lowest_variant.mrp if lowest_variant else 0,
                "image": primary_image,
                "in_stock": any(v.stock_quantity > 0 for v in product.variants.all()),
            }
        )

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
    }

    return render(request, "user/filter.html", context)

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def checkout(request):
    if not request.user.is_authenticated:
        return redirect("all_login")

    user = request.user
    cart = (
        Cart.objects.filter(user=user)
        .prefetch_related("items__variant__product__seller", "items__variant__images")
        .first()
    )

    if not cart or not cart.items.exists():
        return render(request, "user/checkout.html", {"error": "Your cart is empty"})

    addresses = user.addresses.all().order_by("-is_default", "-id")
    subtotal = cart.total_amount
    shipping = Decimal("99") if subtotal < 999 else Decimal("0")
    tax_amount = subtotal * Decimal("0.18")
    grand_total = subtotal + shipping + tax_amount

    context = {
        "cart": cart,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
    }

    if request.method == "POST":
        address_id = request.POST.get("selected_address_id")
        payment_method = request.POST.get("payment_method")

        if not address_id:
            context["error"] = "Please select a delivery address"
            return render(request, "user/checkout.html", context)

        if not payment_method:
            context["error"] = "Please select a payment method"
            return render(request, "user/checkout.html", context)

        address = get_object_or_404(Address, id=address_id, user=user)
        order_number = f"EB{timezone.now().strftime('%Y%m%d')}{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        shipping_address = f"{address.house_info}, {address.locality}, {address.city}, {address.state} - {address.pincode}"

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                total_amount=grand_total,
                payment_status="PENDING",
                order_status="CONFIRMED",
                shipping_name=address.full_name,
                shipping_phone=address.phone_number,
                shipping_address=shipping_address,
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    seller=item.variant.product.seller,
                    quantity=item.quantity,
                    price_at_purchase=item.price_at_time,
                )

                item.variant.stock_quantity -= item.quantity
                item.variant.save()

            cart.items.all().delete()
            cart.total_amount = 0
            cart.save()
        
        # Send WhatsApp notification for order confirmation
        if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
            whatsapp_notifier.send_order_confirmation(order)

        return render(
            request,
            "user/order_success.html",
            {"order": order, "payment_method": payment_method},
        )

    return render(request, "user/checkout.html", context)


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def display_order(request):
    user = request.user
    order_items = (
        OrderItem.objects
        .filter(order__user=user)
        .select_related("order", "variant__product", "seller", "seller__user")
        .prefetch_related("variant__images")
        .order_by("-order__ordered_at")
    )
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
            item.variant.stock_quantity += item.quantity
            item.variant.save()
            item.save()
    return JsonResponse({"success": True, "message": "Order cancelled successfully"})


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def buy_now(request, variant_id):
    if not request.user.is_authenticated:
        return redirect("all_login")

    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.stock_quantity <= 0:
        return render(
            request, "user/checkout.html", {"error": "Product is out of stock"}
        )

    addresses = request.user.addresses.all().order_by("-is_default", "-id")

    subtotal = variant.selling_price
    shipping = Decimal("99") if subtotal < 999 else Decimal("0")
    tax_amount = subtotal * Decimal("0.18")
    grand_total = subtotal + shipping + tax_amount

    context = {
        "single_product": True,
        "variant": variant,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
    }

    if request.method == "POST":
        address_id = request.POST.get("selected_address_id")
        payment_method = request.POST.get("payment_method")

        if not address_id:
            context["error"] = "Please select a delivery address"
            return render(request, "user/checkout.html", context)

        if not payment_method:
            context["error"] = "Please select a payment method"
            return render(request, "user/checkout.html", context)

        address = get_object_or_404(Address, id=address_id, user=request.user)
        order_number = f"EB{timezone.now().strftime('%Y%m%d')}{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        shipping_address = f"{address.house_info}, {address.locality}, {address.city}, {address.state} - {address.pincode}"

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                total_amount=grand_total,
                payment_status="PENDING",
                order_status="CONFIRMED",
                shipping_name=address.full_name,
                shipping_phone=address.phone_number,
                shipping_address=shipping_address,
            )

            OrderItem.objects.create(
                order=order,
                variant=variant,
                seller=variant.product.seller,
                quantity=1,
                price_at_purchase=variant.selling_price,
            )

            variant.stock_quantity -= 1
            variant.save()
        
        # Send WhatsApp notification for order confirmation
        if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
            whatsapp_notifier.send_order_confirmation(order)

        return render(
            request,
            "user/order_success.html",
            {"order": order, "payment_method": payment_method},
        )

    return render(request, "user/checkout.html", context)


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def profile_settings(request):
    user = request.user
    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == "POST":
        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")
        user.phone_number = request.POST.get("phone_number")
        user.dob = request.POST.get("dob") if request.POST.get("dob") else None
        user.gender = request.POST.get("gender")
        if request.FILES.get("profile_image"):
            user.profile_image = request.FILES.get("profile_image")
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
    if request.method == "POST":
        full_name = request.POST.get("fullname")
        phone = request.POST.get("phone")
        pincode = request.POST.get("pincode")
        locality = request.POST.get("locality")
        house = request.POST.get("house_info")
        city = request.POST.get("city")
        state = request.POST.get("state")
        addr_type = request.POST.get("address_type")
        is_default = request.POST.get("is_default") == "on"
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone,
            pincode=pincode,
            locality=locality,
            house_info=house,
            city=city,
            state=state,
            address_type=addr_type,
            is_default=is_default,
        )
        return redirect("manage_addresses")


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def edit_address(request, id):
    address = Address.objects.get(id=id, user=request.user)
    if request.method == "POST":
        address.full_name = request.POST.get("fullname")
        address.phone_number = request.POST.get("phone")
        address.house_info = request.POST.get("house_info")
        address.locality = request.POST.get("locality")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = request.POST.get("pincode")
        address.address_type = request.POST.get("address_type")
        is_default = request.POST.get("is_default") == "on"
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
            address.is_default = True
        else:
            address.is_default = False
        address.save()
    return redirect("manage_addresses")


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def delete_address(request, id):
    address = Address.objects.get(id=id, user=request.user)
    address.delete()
    return redirect("manage_addresses")


# ============================================
# WISHLIST VIEWS
# ============================================

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def toggle_wishlist(request, variant_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    user = request.user
    wishlist, _ = Wishlist.objects.get_or_create(
        user=user,
        wishlist_name="My Wishlist"
    )
    wishlist_item = WishlistItem.objects.filter(wishlist=wishlist, variant=variant).first()
    if wishlist_item:
        wishlist_item.delete()
        return JsonResponse({
            "success": True,
            "action": "removed",
            "message": "Removed from wishlist",
            "in_wishlist": False
        })
    else:

        WishlistItem.objects.create(wishlist=wishlist, variant=variant)
        return JsonResponse({
            "success": True,
            "action": "added",
            "message": "Added to wishlist",
            "in_wishlist": True
        })


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def wishlist_view(request):
    user = request.user
    wishlist = Wishlist.objects.filter(user=user, wishlist_name="My Wishlist").first()
    if not wishlist:
        return render(request, "user/wishlist.html", {"page_obj": None})
    items = (
        WishlistItem.objects
        .filter(wishlist=wishlist)
        .select_related("variant__product", "variant__product__seller")
        .prefetch_related("variant__images")
        .order_by("-added_at")
    )

    paginator = Paginator(items, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "user/wishlist.html", {"page_obj": page_obj, "wishlist": wishlist})


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def remove_from_wishlist(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    wishlist_item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user
    )
    wishlist_item.delete()
    return JsonResponse({
        "success": True,
        "message": "Item removed from wishlist"
    })


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def manage_wishlists(request):
    user = request.user
    wishlists = Wishlist.objects.filter(user=user).prefetch_related('items__variant__images').order_by('-created_at')
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
        return JsonResponse({"success": False, "message": "Wishlist with this name already exists"})

    Wishlist.objects.create(user=request.user, wishlist_name=wishlist_name)
    return JsonResponse({"success": True, "message": "Wishlist created successfully"})


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

    if Wishlist.objects.filter(user=request.user, wishlist_name=wishlist_name).exclude(id=wishlist_id).exists():
        return JsonResponse({"success": False, "message": "Wishlist with this name already exists"})

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
        return JsonResponse({"success": False, "message": "Cannot delete default wishlist"})

    wishlist.delete()
    return JsonResponse({"success": True, "message": "Wishlist deleted successfully"})


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def move_to_cart(request, item_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    wishlist_item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user
    )

    variant = wishlist_item.variant

    if variant.stock_quantity <= 0:
        return JsonResponse({"success": False, "message": "Product is out of stock"})


    cart, _ = Cart.objects.get_or_create(user=request.user)


    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={"quantity": 1, "price_at_time": variant.selling_price}
    )

    if not created:
        if cart_item.quantity + 1 <= variant.stock_quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({
                "success": False,
                "message": f"Only {variant.stock_quantity} items available"
            })
    total = sum(item.quantity * item.price_at_time for item in cart.items.all())
    cart.total_amount = total
    cart.save()

    wishlist_item.delete()

    return JsonResponse({
        "success": True,
        "message": "Item moved to cart successfully"
    })
def best_seller(request):
    best_selling_variants = (
        ProductVariant.objects
        .filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED"
        )
        .annotate(total_sold=Sum('orderitem__quantity'))
        .filter(total_sold__gt=0)
        .select_related('product', 'product__seller')
        .prefetch_related('images')
        .order_by('-total_sold')
    )

    wishlist_variant_ids = set()
    if request.user.is_authenticated:
        variant_ids = [v.id for v in best_selling_variants]
        wishlist_items = WishlistItem.objects.filter(
            wishlist__user=request.user,
            variant_id__in=variant_ids
        ).values_list('variant_id', flat=True)
        wishlist_variant_ids = set(wishlist_items)

    product_data = []
    for variant in best_selling_variants:
        primary_image = None
        for img in variant.images.filter(is_primary=True):
            if img.image:
                primary_image = img
                break
        if not primary_image:
            for img in variant.images.all():
                if img.image:
                    primary_image = img
                    break
        product_data.append({
            "variant": variant,
            "image": primary_image,
            "total_sold": variant.total_sold,
            "in_wishlist": variant.id in wishlist_variant_ids
        })

    paginator = Paginator(product_data, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "user/best_sellers.html", {"page_obj": page_obj})


def get_brands_ajax(request):
    """AJAX endpoint to get brands based on category/subcategory/search filters"""
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    category = request.GET.get("category")
    subcategory = request.GET.get("subcategory")
    search = request.GET.get("search")

    brand_query = Product.objects.filter(
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED"
    )

    if category:
        brand_query = brand_query.filter(subcategory__category__slug=category)
    if subcategory:
        brand_query = brand_query.filter(subcategory__slug=subcategory)
    if search:
        search_query = search.strip()
        brand_query = brand_query.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )

    brands = (
        brand_query
        .values_list("brand", flat=True)
        .distinct()
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
        .order_by("brand")
    )

    return JsonResponse({
        "brands": list(brands),
        "count": len(brands)
    })


def get_subcategories_ajax(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    category = request.GET.get("category")
    if category:

        subcategories = SubCategory.objects.filter(
            category__slug=category,
            is_active=True
        ).values('slug', 'name').order_by('name')
    else:

        subcategories = SubCategory.objects.filter(
            is_active=True
        ).values('slug', 'name').order_by('name')

    return JsonResponse({
        "subcategories": list(subcategories),
        "count": len(subcategories)
    })


def search_autocomplete(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(brand__icontains=query),
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED"
    ).values('name', 'slug', 'brand').distinct()[:5]

    categories = Category.objects.filter(
        name__icontains=query,
        is_active=True
    ).values('name', 'slug')[:3]

    brands = Product.objects.filter(
        brand__icontains=query,
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED"
    ).values_list('brand', flat=True).distinct()[:3]

    suggestions = {
        "products": list(products),
        "categories": list(categories),
        "brands": list(brands),
        "query": query
    }

    return JsonResponse(suggestions)


# ============================================
# REVIEW ENHANCEMENT VIEWS
# ============================================

@login_required
@role_required(allowed_roles=["CUSTOMER"])
def toggle_review_helpful(request, review_id):
    """Toggle helpful vote on a review"""
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    
    review = get_object_or_404(Review, id=review_id)
    user = request.user
    
    # Check if user already voted
    helpful_vote = ReviewHelpful.objects.filter(review=review, user=user).first()
    
    if helpful_vote:
        # Remove vote
        helpful_vote.delete()
        review.helpful_count = max(0, review.helpful_count - 1)
        review.save()
        return JsonResponse({
            "success": True,
            "action": "removed",
            "helpful_count": review.helpful_count,
            "message": "Vote removed"
        })
    else:
        # Add vote
        ReviewHelpful.objects.create(review=review, user=user)
        review.helpful_count += 1
        review.save()
        return JsonResponse({
            "success": True,
            "action": "added",
            "helpful_count": review.helpful_count,
            "message": "Marked as helpful"
        })
