from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from .models import ProductVariant, Cart, CartItem
from easybuy.core.models import SubCategory, Category
from easybuy.seller.models import Product, ProductVariant
from .models import Cart, CartItem
from django.http import JsonResponse
import json


def new_arrival(request):
    products = Product.objects.filter(
        is_active=True,
    ).order_by("-created_at")[:8]
    return render(request, "user/new_arrivals.html", {"products": products})


def category_products(request, slug=None, id=None):
    """Category products page - uses slug for lookup, falls back to id for backward compatibility"""
    if slug:
        categories = get_object_or_404(Category, slug=slug, is_active=True)
    elif id:
        # Backward compatibility - fallback to id lookup
        categories = get_object_or_404(Category, id=id, is_active=True)
    else:
        from django.http import Http404

        raise Http404("Category not found")

    subcategory = SubCategory.objects.filter(category=categories, is_active=True)
    product = Product.objects.filter(
        subcategory__category=categories,
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED",
    ).prefetch_related("variants__images")
    return render(
        request,
        "core/category_products.html",
        {
            "categories": categories,
            "subcategory": subcategory,
            "product": product,
            "active_sub": None,
        },
    )


def subcategory_products(request, slug=None, id=None):
    """Subcategory products page - uses slug for lookup, falls back to id for backward compatibility"""
    if slug:
        current_sub = get_object_or_404(SubCategory, slug=slug, is_active=True)
    elif id:
        # Backward compatibility - fallback to id lookup
        current_sub = get_object_or_404(SubCategory, id=id, is_active=True)
    else:
        from django.http import Http404

        raise Http404("Subcategory not found")

    categories = current_sub.category
    subcategory = SubCategory.objects.filter(category=categories, is_active=True)
    product = Product.objects.filter(
        subcategory=current_sub,
        is_active=True,
        approval_status="APPROVED",
        seller__status="APPROVED",
    ).prefetch_related("variants__images")

    return render(
        request,
        "core/category_products.html",
        {
            "categories": categories,
            "subcategory": subcategory,
            "product": product,
            "active_sub": current_sub.id,
        },
    )


def product_detail(request, slug=None, id=None):
    """Product detail page - uses slug for lookup, falls back to id for backward compatibility"""
    if slug:
        product = (
            Product.objects.filter(
                slug=slug,
                is_active=True,
            )
            .prefetch_related("variants__images")
            .first()
        )
    elif id:
        # Backward compatibility - fallback to id lookup
        product = (
            Product.objects.filter(
                id=id,
                is_active=True,
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
    return render(request, "user/product_details.html", {"product": product})


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


role_required(allowed_roles=["CUSTOMER"])


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


@login_required
@role_required(allowed_roles=["CUSTOMER"])
def single_product(request, slug):
    product = (
        Product.objects.prefetch_related("variants__images")
        .filter(
            slug=slug,
            is_active=True,
           
        )
        .first()
    )
    if not product:
        from django.http import Http404

        raise Http404("Product not found")
    return render(request, "user/single_view.html", {"product": product})
