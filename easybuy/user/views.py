from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from .models import ProductVariant, Cart, CartItem
from easybuy.core.models import SubCategory, Category, Address
from easybuy.seller.models import Product, ProductVariant
from .models import Cart, CartItem, Order, OrderItem
from django.http import JsonResponse
import json
from django.http import Http404
from django.db.models import Q
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
import random
import string


def new_arrival(request):
    products = Product.objects.filter(
        is_active=True,
    ).order_by(
        "-created_at"
    )[:8]
    return render(request, "user/new_arrivals.html", {"products": products})


def category_products(request, slug=None, id=None):
    if slug:
        categories = get_object_or_404(Category, slug=slug, is_active=True)
    elif id:
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
    if slug:
        current_sub = get_object_or_404(SubCategory, slug=slug, is_active=True)
    elif id:
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
        raise Http404("Product not found")
    return render(request, "user/single_view.html", {"product": product})


def filtering(request):
    products = (
        Product.objects.filter(is_active=True)
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
    if icategory:
        products = products.filter(subcategory__category__slug=icategory)
    if isubCategory:
        products = products.filter(subcategory__slug=isubCategory)

    if ibrand:
        products = products.filter(brand__in=ibrand)

    if iprod:
        search_query = iprod.strip()
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(brand__icontains=search_query)
        )
    all_brands = (
        Product.objects.filter(is_active=True)
        .values_list("brand", flat=True)
        .distinct()
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
        primary_image = (
            product.variants.all().first().images.filter(is_primary=True).first()
            or product.variants.all().first().images.first()
        )

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
    orders = (
        Order.objects.prefetch_related(
            "items__variant__product", "items__variant__images"
        )
        .filter(user=user)
        .order_by("-ordered_at")
    )
    return render(request, "user/orders.html", {"orders": orders})


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

        return render(
            request,
            "user/order_success.html",
            {"order": order, "payment_method": payment_method},
        )

    return render(request, "user/checkout.html", context)
