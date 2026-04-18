from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.text import slugify
from django.db import transaction
from django.db.models import F, Sum, Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import json
import logging
import traceback
import random
import string
from core.decorators import role_required, approved_seller_required
from easybuy_admin.models import Coupon
from .models import SellerProfile, Product, ProductVariant, ProductImage, InventoryLog
from core.models import SubCategory
from user.models import Order, OrderItem, Review, ReturnRequest
from core.whatsapp_utils import whatsapp_notifier
from django.db import transaction, IntegrityError
from decimal import Decimal, InvalidOperation
from django.core.mail import send_mail
from django.urls import reverse
from core.notifications import send_status_change_notification


User = get_user_model()
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_ORDER_STATUS_TRANSITIONS = {
    "PENDING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
    "RETURN_REQUESTED": set(),
    "RETURNED": set(),
}


def generate_sku(length=8):
    """Generate a random SKU: uppercase letters + digits."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_unique_store_slug(store_name):
    base_slug = slugify(store_name) or "seller-store"
    unique_slug = base_slug
    counter = 1

    while SellerProfile.objects.filter(store_slug=unique_slug).exists():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    return unique_slug


def seller_shell_context(request, active_menu=None, **extra):
    context = {"active_menu": active_menu}
    seller_profile = (
        getattr(request.user, "seller_profile", None)
        if request.user.is_authenticated
        else None
    )
    if seller_profile is not None:
        context["seller_profile"] = seller_profile
    context.update(extra)
    return context


def _validate_upload(file_obj, *, allowed_content_types, label):
    content_type = (getattr(file_obj, "content_type", "") or "").lower()
    if content_type and content_type not in allowed_content_types:
        return f"{label} has an unsupported file type."
    if file_obj.size > MAX_UPLOAD_BYTES:
        return f"{label} must be under 5MB."
    return ""


def _parse_promo_datetime(raw_value):
    dt = datetime.fromisoformat(raw_value)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def seller_regi_success(request):
    return render(request, "seller/seller_registration_success.html")


@login_required
@role_required(allowed_roles=["SELLER"])
def seller_waiting(request):
    seller_profile = getattr(request.user, "seller_profile", None)
    if seller_profile is None:
        messages.error(request, "Complete your seller registration to continue.")
        return redirect("seller_register")

    if seller_profile.status == "APPROVED":
        return redirect("seller_dashboard")

    return render(
        request,
        "seller/seller_waiting.html",
        seller_shell_context(
            request,
            active_menu=None,
            seller=seller_profile,
        ),
    )


def seller_regi(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        store_name = request.POST.get("store_name")
        gst_number = request.POST.get("gst_number")
        pan_number = request.POST.get("pan_number")
        doc = request.FILES.get("doc")
        bank_account_number = request.POST.get("bank_account_number")
        ifsc_code = request.POST.get("ifsc_code")
        business_address = request.POST.get("business_address")
        if User.objects.filter(username=username).exists():
            return render(
                request,
                "seller/sellerregistration.html",
                {
                    "error": "Username already exists. Please choose a different username.",
                    "username": username,
                    "email": email,
                    "store_name": store_name,
                    "gst_number": gst_number,
                    "pan_number": pan_number,
                    "bank_account_number": bank_account_number,
                    "ifsc_code": ifsc_code,
                    "business_address": business_address,
                },
            )
        if email and User.objects.filter(email=email).exists():
            return render(
                request,
                "seller/sellerregistration.html",
                {
                    "error": "Email already registered. Please use a different email.",
                    "username": username,
                    "email": email,
                    "store_name": store_name,
                    "gst_number": gst_number,
                    "pan_number": pan_number,
                    "bank_account_number": bank_account_number,
                    "ifsc_code": ifsc_code,
                    "business_address": business_address,
                },
            )
        if doc:
            validation_error = _validate_upload(
                doc,
                allowed_content_types=ALLOWED_DOCUMENT_CONTENT_TYPES,
                label="Business document",
            )
            if validation_error:
                return render(
                    request,
                    "seller/sellerregistration.html",
                    {
                        "error": validation_error,
                        "username": username,
                        "email": email,
                        "store_name": store_name,
                        "gst_number": gst_number,
                        "pan_number": pan_number,
                        "bank_account_number": bank_account_number,
                        "ifsc_code": ifsc_code,
                        "business_address": business_address,
                    },
                )

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    role="SELLER",
                )
                SellerProfile.objects.create(
                    user=user,
                    store_name=store_name,
                    store_slug=generate_unique_store_slug(store_name),
                    gst_number=gst_number,
                    pan_number=pan_number,
                    doc=doc,
                    status="PENDING",
                    bank_account_number=bank_account_number,
                    ifsc_code=ifsc_code,
                    business_address=business_address,
                )
            return redirect("seller_registration_success")
        except Exception as e:
            return render(
                request,
                "seller/sellerregistration.html",
                {
                    "error": f"Registration failed: {str(e)}",
                    "username": username,
                    "email": email,
                    "store_name": store_name,
                    "gst_number": gst_number,
                    "pan_number": pan_number,
                    "bank_account_number": bank_account_number,
                    "ifsc_code": ifsc_code,
                    "business_address": business_address,
                },
            )
    return render(request, "seller/sellerregistration.html")


@approved_seller_required
def seller_product_list(request):
    sellers = SellerProfile.objects.prefetch_related("product_set").all()
    return render(request, "seller/inventory.html", {"sellers": sellers})


@approved_seller_required
def seller_dashboard(request):
    seller = request.user.seller_profile
    now = timezone.now()

    order_items = OrderItem.objects.filter(seller=seller)

    stats = order_items.aggregate(
        total_orders=Count("id"),
        total_revenue=Sum(F("price_at_purchase") * F("quantity")),
        pending_orders=Count("id", filter=Q(status="PENDING")),
        delivered_revenue=Sum(
            F("price_at_purchase") * F("quantity"),
            filter=Q(order__order_status="DELIVERED"),
        ),
        pending_count=Count("id", filter=Q(status="PENDING")),
        shipped_count=Count("id", filter=Q(status="SHIPPED")),
        delivered_count=Count("id", filter=Q(status="DELIVERED")),
        cancelled_count=Count("id", filter=Q(status="CANCELLED")),
    )

    total_orders = stats["total_orders"] or 0
    total_revenue = float(stats["total_revenue"] or 0)
    pending_orders = stats["pending_orders"] or 0
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    delivered_revenue = float(stats["delivered_revenue"] or 0)

    recent_orders = order_items.select_related("order", "variant__product").order_by(
        "-order__ordered_at"
    )[:5]

    total_products = Product.objects.filter(seller=seller).count()
    active_products = Product.objects.filter(seller=seller, is_active=True).count()

    revenue_by_day = {
        row["day"]: float(row["revenue"] or 0)
        for row in order_items.filter(order__ordered_at__gte=now - timedelta(days=6))
        .annotate(day=TruncDate("order__ordered_at"))
        .values("day")
        .annotate(revenue=Sum(F("price_at_purchase") * F("quantity")))
        .order_by("day")
    }

    daily_revenue = []
    daily_labels = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        daily_labels.append(date.strftime("%b %d"))
        daily_revenue.append(round(revenue_by_day.get(date.date(), 0), 2))

    top_products = (
        order_items.values("variant__product__name")
        .annotate(
            total_sold=Sum("quantity"),
            revenue=Sum(F("price_at_purchase") * F("quantity")),
        )
        .order_by("-total_sold")[:5]
    )

    status_counts = {
        "PENDING": stats["pending_count"] or 0,
        "SHIPPED": stats["shipped_count"] or 0,
        "DELIVERED": stats["delivered_count"] or 0,
        "CANCELLED": stats["cancelled_count"] or 0,
    }

    inventory_history = (
        InventoryLog.objects.filter(
            variant__product__seller=seller,
            created_at__gte=now - timedelta(days=6),
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            stock_in=Sum("change_amount", filter=Q(change_amount__gt=0)),
            stock_out=Sum("change_amount", filter=Q(change_amount__lt=0)),
        )
        .order_by("day")
    )

    inv_by_day = {
        row["day"]: {
            "stock_in": float(row["stock_in"] or 0),
            "stock_out": float(row["stock_out"] or 0),
        }
        for row in inventory_history
    }

    inv_labels = []
    inv_changes = []
    total_stock_in = 0
    total_stock_out = 0
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        inv_labels.append(date.strftime("%b %d"))
        day_data = inv_by_day.get(date.date(), {"stock_in": 0, "stock_out": 0})
        stock_in = day_data["stock_in"]
        stock_out = day_data["stock_out"]
        inv_changes.append(stock_in + stock_out)
        total_stock_in += stock_in
        total_stock_out += abs(stock_out)

    net_stock_movement = total_stock_in - total_stock_out
    low_stock_items = ProductVariant.objects.filter(
        product__seller=seller, stock_quantity__lte=10, stock_quantity__gt=0
    ).select_related("product")[:5]

    context = seller_shell_context(
        request,
        active_menu="dashboard",
        seller=seller,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        total_products=total_products,
        active_products=active_products,
        average_order_value=average_order_value,
        delivered_revenue=delivered_revenue,
        daily_labels_data=json.dumps(daily_labels),
        daily_revenue_data=json.dumps(daily_revenue),
        daily_inv_labels_data=json.dumps(inv_labels),
        daily_inv_changes_data=json.dumps(inv_changes),
        total_stock_in=total_stock_in,
        total_stock_out=total_stock_out,
        net_stock_movement=net_stock_movement,
        top_products=top_products,
        status_counts=status_counts,
        recent_orders=recent_orders,
        low_stock_items=low_stock_items,
    )

    return render(request, "seller/dashboard.html", context)


@approved_seller_required
def seller_inventory(request):
    seller = request.user.seller_profile

    if seller:
        variants = (
            ProductVariant.objects.filter(product__seller=seller)
            .select_related("product", "product__subcategory")
            .prefetch_related("images")
            .order_by("-id")
        )
        total_stock = 0
        total_inventory_value = 0
        low_stock_count = 0
        out_of_stock_count = 0

        for item in variants:
            total_stock += item.stock_quantity
            total_inventory_value += float(item.selling_price) * item.stock_quantity

            if item.stock_quantity == 0:
                out_of_stock_count += 1
            elif item.stock_quantity <= 10:
                low_stock_count += 1

        paginator = Paginator(variants, 5)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    else:
        page_obj = None
        total_stock = 0
        total_inventory_value = 0
        low_stock_count = 0
        out_of_stock_count = 0

    context = seller_shell_context(
        request,
        active_menu="inventory",
        page_obj=page_obj,
        total_products=(Product.objects.filter(seller=seller).count() if seller else 0),
        total_variants=(variants.count() if seller else 0),
        total_stock=total_stock,
        total_inventory_value=total_inventory_value,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
    )

    return render(request, "seller/inventory.html", context)


@approved_seller_required
def seller_promo_codes(request):
    seller = request.user.seller_profile

    if request.method == "POST":
        try:
            product = get_object_or_404(
                Product, id=request.POST.get("product_id"), seller=seller
            )
            valid_from = _parse_promo_datetime(request.POST.get("valid_from"))
            valid_to = _parse_promo_datetime(request.POST.get("valid_to"))
            discount_value = Decimal(request.POST.get("discount_value") or "0")
            min_order_amount = Decimal(request.POST.get("min_order_amount") or "0")
            usage_limit = int(request.POST.get("usage_limit") or 0)

            if valid_to <= valid_from:
                raise ValueError("Promo end date must be after the start date.")
            if discount_value <= 0:
                raise ValueError("Discount value must be greater than 0.")
            if min_order_amount < 0 or usage_limit < 0:
                raise ValueError("Minimum subtotal and usage limit cannot be negative.")

            Coupon.objects.create(
                seller=seller,
                product=product,
                name=(request.POST.get("name") or "").strip(),
                code=(request.POST.get("code") or "").strip().upper(),
                discount_type=(request.POST.get("discount_type") or "PERCENT")
                .strip()
                .upper(),
                discount_value=discount_value,
                valid_from=valid_from,
                valid_to=valid_to,
                usage_limit=usage_limit,
                min_order_amount=min_order_amount,
                is_active=request.POST.get("is_active") == "on",
            )
            messages.success(request, "Product promo code created successfully.")
            return redirect("seller_promo_codes")
        except (InvalidOperation, TypeError):
            messages.error(request, "Please enter valid promo code details.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, str(exc))

    promo_codes = (
        Coupon.objects.filter(seller=seller)
        .select_related("product")
        .order_by("-created_at")
    )
    products = Product.objects.filter(seller=seller).order_by("name")
    return render(
        request,
        "seller/promo_codes.html",
        seller_shell_context(
            request,
            active_menu="promotions",
            promo_codes=promo_codes,
            products=products,
        ),
    )


@approved_seller_required
def toggle_seller_promo_code(request, coupon_id):
    if request.method != "POST":
        return redirect("seller_promo_codes")

    coupon = get_object_or_404(Coupon, id=coupon_id, seller=request.user.seller_profile)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=["is_active"])
    state = "activated" if coupon.is_active else "disabled"
    messages.success(request, f"Promo code '{coupon.code}' {state}.")
    return redirect("seller_promo_codes")


@approved_seller_required
def add_product(request):

    if request.method == "POST":

        # Normalize
        name = request.POST.get("name", "").strip()
        description = request.POST.get("des", "").strip()
        brand = request.POST.get("brand", "").strip()
        model = request.POST.get("model", "").strip()
        subcategory_id = request.POST.get("subcategory")

        # Required validation
        if not name:
            messages.error(request, "Product name is required.")
            return redirect("add_product")

        if len(name) < 3:
            messages.error(request, "Product name must be at least 3 characters.")
            return redirect("add_product")

        if not subcategory_id:
            messages.error(request, "Please select a subcategory.")
            return redirect("add_product")

        # Subcategory validation
        try:
            subcategory_obj = SubCategory.objects.get(id=subcategory_id)
        except SubCategory.DoesNotExist:
            messages.error(request, "Invalid subcategory selected.")
            return redirect("add_product")

        # Boolean handling
        is_cancellable = request.POST.get("cancellable") == "on"
        is_returnable = request.POST.get("returnable") == "on"
        is_active = request.POST.get("is_active") == "on"

        # Return days
        try:
            return_days = int(request.POST.get("return_days") or 0)
        except ValueError:
            messages.error(request, "Return days must be a number.")
            return redirect("add_product")

        if is_returnable and return_days <= 0:
            messages.error(request, "Return days must be greater than 0.")
            return redirect("add_product")

        if not is_returnable:
            return_days = 0

        if Product.objects.filter(
            seller=request.user.seller_profile,
            name__iexact=name,
            model_number__iexact=model,
        ).exists():
            messages.error(request, "Product already exists.")
            return redirect("add_product")

        try:
            product = Product.objects.create(
                seller=request.user.seller_profile,
                subcategory=subcategory_obj,
                name=name,
                description=description,
                brand=brand,
                model_number=model,
                is_cancellable=is_cancellable,
                is_returnable=is_returnable,
                is_active=is_active,
                return_days=return_days,
            )

        except Exception:
            messages.error(request, "Failed to create product.")
            return redirect("add_product")

        messages.success(request, "Product created. Now add variants.")
        return redirect("add_variant", product_id=product.id)

    subcategories = SubCategory.objects.filter(is_active=True).select_related(
        "category"
    )

    return render(
        request,
        "seller/add_product.html",
        seller_shell_context(
            request,
            active_menu="add_product",
            subcategories=subcategories,
        ),
    )


@approved_seller_required
def add_variant(request, product_id):

    product = get_object_or_404(
        Product, id=product_id, seller=request.user.seller_profile
    )

    if request.method == "POST":

        required_fields = {"mrp": "MRP", "price": "Selling price", "stock": "Stock"}

        for field, name in required_fields.items():
            if not request.POST.get(field):
                messages.error(request, f"{name} is required.")
                return redirect("add_variant", product_id=product.id)

        images = request.FILES.getlist("images")
        if not images:
            messages.error(request, "At least one image is required.")
            return redirect("add_variant", product_id=product.id)

        try:
            mrp = Decimal(request.POST.get("mrp"))
            price = Decimal(request.POST.get("price"))
            cost = Decimal(request.POST.get("cost") or 0)

            stock = int(request.POST.get("stock"))

            tax = Decimal(request.POST.get("tax") or 0)

            weight = Decimal(request.POST.get("weight") or 0)
            length = Decimal(request.POST.get("length") or 0)
            width = Decimal(request.POST.get("width") or 0)
            height = Decimal(request.POST.get("height") or 0)

        except (InvalidOperation, ValueError):
            messages.error(request, "Invalid numeric input.")
            return redirect("add_variant", product_id=product.id)

        if mrp <= 0:
            messages.error(request, "MRP must be greater than 0.")
            return redirect("add_variant", product_id=product.id)

        if price <= 0:
            messages.error(request, "Selling price must be greater than 0.")
            return redirect("add_variant", product_id=product.id)

        if stock < 0:
            messages.error(request, "Stock cannot be negative.")
            return redirect("add_variant", product_id=product.id)

        if price > mrp:
            messages.error(request, "Selling price cannot exceed MRP.")
            return redirect("add_variant", product_id=product.id)
        if price < cost:
            messages.error(request, "Selling price cannot be less than cost price.")
            return redirect("add_variant", product_id=product.id)

        if cost < 0:
            messages.error(request, "Cost price cannot be negative.")
            return redirect("add_variant", product_id=product.id)

        if tax < 0:
            messages.error(request, "Tax cannot be negative.")
            return redirect("add_variant", product_id=product.id)
        for value, name in [
            (weight, "Weight"),
            (length, "Length"),
            (width, "Width"),
            (height, "Height"),
        ]:
            if value < 0:
                messages.error(request, f"{name} cannot be negative.")
                return redirect("add_variant", product_id=product.id)

        for img in images:
            validation_error = _validate_upload(
                img,
                allowed_content_types=ALLOWED_IMAGE_CONTENT_TYPES,
                label=f"Image '{img.name}'",
            )
            if validation_error:
                messages.error(request, validation_error)
                return redirect("add_variant", product_id=product.id)

        try:
            primary_image_index = int(request.POST.get("primary_image_index") or 0)
        except (ValueError, TypeError):
            primary_image_index = 0
        primary_image_index = max(0, min(primary_image_index, len(images) - 1))

        try:
            with transaction.atomic():

                variant = ProductVariant.objects.create(
                    product=product,
                    sku_code=generate_sku(),
                    mrp=mrp,
                    selling_price=price,
                    cost_price=cost,
                    stock_quantity=stock,
                    weight=weight,
                    length=length,
                    width=width,
                    height=height,
                    tax_percentage=tax,
                )

                for idx, img in enumerate(images):
                    ProductImage.objects.create(
                        variant=variant,
                        image=img,
                        is_primary=(idx == primary_image_index),
                    )

        except IntegrityError:
            messages.error(request, "SKU conflict occurred. Please try again.")
            return redirect("add_variant", product_id=product.id)

        except Exception:
            messages.error(request, "Unexpected error occurred.")
            return redirect("add_variant", product_id=product.id)
        if "finish" in request.POST:
            messages.success(request, "Product completed successfully.")
            return redirect("seller_products_list")

        messages.success(request, "Variant added successfully.")
        return redirect("add_variant", product_id=product.id)
    variants = product.variants.all()

    return render(
        request,
        "seller/add_variant.html",
        seller_shell_context(
            request,
            active_menu="manage_variants",
            product=product,
            variants=variants,
        ),
    )


@approved_seller_required
def select_product_for_variant(request):
    products = Product.objects.filter(seller=request.user.seller_profile).order_by(
        "-created_at"
    )

    return render(
        request,
        "seller/select_product_variant.html",
        seller_shell_context(
            request,
            active_menu="manage_variants",
            products=products,
        ),
    )


@approved_seller_required
def add_stock(request):
    if request.method == "POST":
        try:
            item_id = request.POST.get("variant_id")
            stock_to_add = int(request.POST.get("stock_amount", 0))
            reason = request.POST.get("reason", "Manual stock addition")

            if stock_to_add <= 0:
                return JsonResponse({"success": False, "error": "Invalid stock amount"})
            item = ProductVariant.objects.select_related("product").get(
                id=item_id, product__seller=request.user.seller_profile
            )

            old_stock = item.stock_quantity
            item.stock_quantity += stock_to_add
            item.save()
            InventoryLog.objects.create(
                variant=item,
                change_amount=stock_to_add,
                reason=reason,
                performed_by=request.user,
            )

            # Check stock notifications if stock was 0 and now >0
            if old_stock <= 0 and item.stock_quantity > 0:
                from core.services import check_stock_notifications

                check_stock_notifications(item)

            return JsonResponse(
                {
                    "success": True,
                    "new_stock": item.stock_quantity,
                    "message": f"Successfully added {stock_to_add} units",
                }
            )
        except ProductVariant.DoesNotExist:
            return JsonResponse({"success": False, "error": "item not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})


@approved_seller_required
def deactivate(request, id):
    if request.method != "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "POST required"}, status=405
            )
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    try:
        item = ProductVariant.objects.select_related("product").get(
            id=id, product__seller=request.user.seller_profile
        )
        product = item.product

        product.is_active = not product.is_active
        product.save()

        return JsonResponse(
            {
                "success": True,
                "is_active": product.is_active,
                "message": f"Product {'activated' if product.is_active else 'deactivated'} successfully",
            }
        )

    except ProductVariant.DoesNotExist:
        return JsonResponse({"success": False, "error": "item not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@approved_seller_required
def seller_order(request):
    seller = request.user.seller_profile
    status_filter = request.GET.get("status")
    page = request.GET.get("page", 1)

    base_query = (
        OrderItem.objects.filter(seller=seller)
        .select_related("order", "variant", "variant__product")
        .order_by("-order__ordered_at")
    )

    if status_filter:
        base_query = base_query.filter(status=status_filter)

    paginator = Paginator(base_query, 5)
    order_items = paginator.get_page(page)

    all_query = OrderItem.objects.filter(seller=seller).select_related(
        "order", "variant", "variant__product"
    )
    total_orders = all_query.count()
    total_revenue = sum(
        float(item.price_at_purchase * item.quantity) for item in all_query
    )

    pending_orders = OrderItem.objects.filter(seller=seller, status="PENDING").count()
    shipped_orders = OrderItem.objects.filter(seller=seller, status="SHIPPED").count()
    delivered_orders = OrderItem.objects.filter(
        seller=seller, status="DELIVERED"
    ).count()
    cancelled_orders = OrderItem.objects.filter(
        seller=seller, status="CANCELLED"
    ).count()

    context = seller_shell_context(
        request,
        active_menu="orders",
        order_items=order_items,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        shipped_orders=shipped_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        current_status_filter=status_filter,
    )

    return render(request, "seller/orders.html", context)


from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import logging
import traceback

logger = logging.getLogger(__name__)


@approved_seller_required
def status(request, id):
    seller = request.user.seller_profile
    order_item = get_object_or_404(OrderItem, seller=seller, id=id)
    if request.method != "POST":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "POST required"}, status=405
            )
        messages.error(request, "Invalid request method.")
        return redirect("seller_orders")

    new_status = (request.POST.get("status") or "").strip().upper()
    allowed_statuses = {"PENDING", "SHIPPED", "DELIVERED", "CANCELLED"}

    if not new_status:

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "No status provided"}, status=400
            )
        return redirect("seller_orders")

    if new_status not in allowed_statuses:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Invalid status selected"}, status=400
            )
        messages.error(request, "Invalid status selected.")
        return redirect("seller_orders")

    if new_status != order_item.status:
        allowed_next_statuses = ALLOWED_ORDER_STATUS_TRANSITIONS.get(
            order_item.status, set()
        )
        if new_status not in allowed_next_statuses:
            message = (
                f"Cannot change order status from {order_item.status} to {new_status}."
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": message}, status=400)
            messages.error(request, message)
            return redirect("seller_orders")

    try:
        with transaction.atomic():
            old_status = order_item.status
            order_item.status = new_status
            if new_status == "SHIPPED" and not order_item.shipped_at:
                from django.utils import timezone

                order_item.shipped_at = timezone.now()
            elif new_status == "DELIVERED" and not order_item.delivered_at:
                order_item.delivered_at = timezone.now()
            order_item.save()
            logger.info(
                f"Status Change: Order {order_item.order.order_number} | {old_status} -> {new_status} by {request.user.username}"
            )

        # Unified Notifications (In-App & Email) via Helper
        send_status_change_notification(order_item.order.user, order_item, new_status)

        if getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", True):
            logger.info(
                f"WhatsApp notifications enabled, sending for OrderItem {order_item.id} status {new_status}"
            )
            logger.info(f"Target phone: {order_item.order.shipping_phone}")
            logger.info(f"Client ready: {whatsapp_notifier.client is not None}")
            try:
                if new_status == "SHIPPED":

                    result = whatsapp_notifier.send_order_shipped(order_item.order)
                    logger.info(f"Shipped notification result: {result}")
                elif new_status == "DELIVERED":

                    result = whatsapp_notifier.send_order_delivered(order_item.order)
                    logger.info(f"Delivered notification result: {result}")
                    feedback_result = whatsapp_notifier.send_feedback_request(
                        order_item.order
                    )
                    logger.info(f"Feedback notification result: {feedback_result}")
                elif new_status == "CANCELLED":

                    result = whatsapp_notifier.send_order_cancelled(order_item.order)
                    logger.info(f"Cancelled notification result: {result}")
            except Exception as e:
                logger.error(f"WhatsApp Notify Failed for Order {id}: {str(e)}")
        else:
            logger.info("WhatsApp notifications DISABLED - skipping send")

        success_msg = f"Order status updated to {new_status}"

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": success_msg})

        messages.success(request, success_msg)
        return redirect("seller_orders")

    except Exception as e:
        logger.error(f"Critical error in status update: {traceback.format_exc()}")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": "Server Error"}, status=500
            )
        messages.error(request, "An error occurred while updating status.")
        return redirect("seller_orders")


@approved_seller_required
def seller_reviews(request):
    seller = request.user.seller_profile

    reviews = (
        Review.objects.filter(product__seller=seller)
        .select_related("user", "product")
        .prefetch_related("images", "videos", "product__variants__images")
        .order_by("-created_at")
    )

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = seller_shell_context(
        request,
        active_menu="reviews",
        page_obj=page_obj,
    )

    return render(request, "seller/reviews.html", context)


@approved_seller_required
def reply_review(request, review_id):
    seller = request.user.seller_profile
    review = get_object_or_404(
        Review.objects.select_related("product"), id=review_id, product__seller=seller
    )

    if request.method == "POST":
        reply = request.POST.get("reply", "").strip()

        if not reply:
            messages.error(request, "Reply cannot be empty.")
            return redirect("seller_reviews")
        if len(reply) > 500:
            messages.error(request, "Reply must be 500 characters or fewer.")
            return redirect("seller_reviews")

        review.seller_reply = reply
        review.replied_at = timezone.now()
        review.save()

        messages.success(request, "Reply posted successfully!")
        return redirect("seller_reviews")

    return redirect("seller_reviews")


@approved_seller_required
def reply_to_review(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)

    review = get_object_or_404(
        Review.objects.select_related("product__seller"), id=review_id
    )

    if review.product.seller.user != request.user:
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)

    reply = request.POST.get("reply", "").strip()

    if not reply:
        return JsonResponse({"success": False, "message": "Reply cannot be empty"})

    if len(reply) > 500:
        return JsonResponse(
            {"success": False, "message": "Reply too long (max 500 characters)"}
        )

    review.seller_reply = reply
    review.replied_at = timezone.now()
    review.save()

    return JsonResponse(
        {
            "success": True,
            "message": "Reply posted successfully",
            "reply": reply,
            "replied_at": review.replied_at.strftime("%B %d, %Y"),
        }
    )


@approved_seller_required
def seller_returns(request):
    seller = request.user.seller_profile
    status_filter = request.GET.get("status")
    return_requests_qs = (
        ReturnRequest.objects.filter(order_item__seller=seller)
        .select_related(
            "order_item",
            "order_item__variant",
            "order_item__variant__product",
            "order_item__order",
        )
        .order_by("-created_at")
    )

    pending_count = return_requests_qs.filter(status="PENDING").count()
    approved_count = return_requests_qs.filter(status="APPROVED").count()
    rejected_count = return_requests_qs.filter(status="REJECTED").count()

    if status_filter in ["PENDING", "APPROVED", "REJECTED"]:
        return_requests = return_requests_qs.filter(status=status_filter)
    else:
        return_requests = return_requests_qs

    paginator = Paginator(return_requests, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = seller_shell_context(
        request,
        active_menu="returns",
        page_obj=page_obj,
        total_requests=return_requests_qs.count(),
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        current_status_filter=status_filter,
    )
    return render(request, "seller/returns.html", context)


@approved_seller_required
def process_return(request, id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"}, status=405)

    seller = request.user.seller_profile
    return_req = get_object_or_404(ReturnRequest, id=id, order_item__seller=seller)
    action = request.POST.get("action")
    allowed_actions = {"approve", "reject"}

    if return_req.status != "PENDING":
        messages.error(request, "Return request already processed")
        return redirect("seller_returns")

    if action not in allowed_actions:
        messages.error(request, "Invalid return action.")
        return redirect("seller_returns")

    try:
        with transaction.atomic():
            if action == "approve":
                return_req.status = "APPROVED"
                return_req.approved_at = timezone.now()
                return_req.save()

                # Update item status & Restock
                item = return_req.order_item
                item.status = "RETURNED"
                item.save()

                variant = item.variant
                variant.stock_quantity += item.quantity
                variant.save()

                InventoryLog.objects.create(
                    variant=variant,
                    change_amount=item.quantity,
                    reason=f"Return Restock: {item.order.order_number}",
                    performed_by=request.user,
                )
                messages.success(request, "Return approved and item restocked.")
                send_status_change_notification(
                    return_req.order_item.order.user,
                    return_req.order_item,
                    "Approved",
                    is_return=True,
                )

            elif action == "reject":
                return_req.status = "REJECTED"
                return_req.save()

                # Revert item status to DELIVERED
                item = return_req.order_item
                item.status = "DELIVERED"
                item.save()

                messages.success(request, "Return request rejected.")
                send_status_change_notification(
                    return_req.order_item.order.user,
                    return_req.order_item,
                    "Rejected",
                    is_return=True,
                )

    except Exception as e:
        logger.error(f"Error processing return {id}: {e}")
        messages.error(request, "An error occurred processing the return.")

    return redirect("seller_returns")
