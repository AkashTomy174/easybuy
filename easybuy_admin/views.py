from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from core.decorators import role_required
from core.forms import BannerForm
from core.models import Banner, Category, User,SubCategory
from seller.models import SellerProfile, Product
from easybuy_admin.models import Coupon
from user.models import OrderItem
from django.db.models import Sum, F
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from django.db.models import Q

User = get_user_model()


@login_required
@role_required(allowed_roles=["ADMIN"])
def admin_dashboard(request):

    rev_agg = OrderItem.objects.aggregate(
        total_revenue=Sum(F("price_at_purchase") * F("quantity"))
    )
    total_revenue = rev_agg["total_revenue"] or 0

    # --- Counts ---
    total_sellers = User.objects.filter(role="SELLER").count()
    total_users = User.objects.filter(role="CUSTOMER").count()

    daily_revenue = []
    daily_labels = []
    now = timezone.now()
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        day_rev = (
            OrderItem.objects.filter(order__ordered_at__date=date.date()).aggregate(
                day_total=Sum(F("price_at_purchase") * F("quantity"))
            )["day_total"]
            or 0
        )
        daily_revenue.append(round(day_rev, 2))
        daily_labels.append(date.strftime("%b %d"))

    cat_data = (
        OrderItem.objects.values("variant__product__subcategory__category__name")
        .annotate(sales=Sum(F("price_at_purchase") * F("quantity")))
        .order_by("-sales")
    )
    cat_labels = [c["variant__product__subcategory__category__name"] for c in cat_data]
    cat_values = [float(c["sales"] or 0) for c in cat_data]

    top_sellers = (
        User.objects.filter(role="SELLER")
        .annotate(
            total_sales=Sum(
                F("seller_profile__orderitem__price_at_purchase")
                * F("seller_profile__orderitem__quantity")
            )
        )
        .order_by("-total_sales")[:5]
    )

    daily_revenue = [float(x) for x in daily_revenue]

    cat_values = [float(x) for x in cat_values]
    context = {
        "sellers": total_sellers,
        "users": total_users,
        "total_revenue": total_revenue,
        "top_sellers": top_sellers,
        "growth_labels": json.dumps(daily_labels),
        "growth_data": json.dumps(daily_revenue),
        "cat_labels": json.dumps(cat_labels),
        "cat_values": json.dumps(cat_values),
    }
    return render(request, "admin/admin_dashboard.html", context)


def admin_email(email, seller_name, status, reason=None):
    if not email:
        return False

    if status == "APPROVED":
        subject = "Seller Account Approved"
        message = f"""Hello {seller_name},


Congratulations! Your seller account has been approved.
You can now log in and start listing your products.

Best Regards,
E-commerce Team"""
    elif status == "REJECTED":
        subject = "Seller Account Rejected"
        message = f"""Hello {seller_name},

We regret to inform you that your seller account application has been rejected."""
        if reason:
            message += f"""

**Rejection Reason:**
{reason}

Please address this issue and reapply if needed."""
        message += f"""

Please contact support for more information.

Best Regards,
E-commerce Team"""
    elif status == "PRODUCT_REJECTED":
        subject = "Product Listing Rejected"
        message = f"""Hello {seller_name},

Your product listing has been rejected."""
        if reason:
            message += f"""

**Rejection Reason:**
{reason}

Please review and resubmit after corrections."""
        message += f"""

Best Regards,
E-commerce Team"""

    else:
        return False

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
    except Exception:
        pass

    return True


@login_required
@role_required(allowed_roles=["ADMIN"])
def approve_seller(request, id):
    if request.method != "POST":
        return redirect("seller_veri")
    seller = get_object_or_404(SellerProfile, id=id)
    seller.status = "APPROVED"
    seller.save()
    seller_email = seller.user.email
    seller_name = seller.store_name
    admin_email(seller_email, seller_name, "APPROVED")

    messages.success(request, f"Seller '{seller.store_name}' has been approved!")
    return redirect("seller_veri")


@login_required
@role_required(allowed_roles=["ADMIN"])
def reject_seller(request, id):
    if request.method != "POST":
        return redirect("seller_veri")
    seller = get_object_or_404(SellerProfile, id=id)
    reason = request.POST.get("reason") if request.method == "POST" else None
    seller.rejection_reason = reason
    seller.status = "REJECTED"
    seller.save()
    seller_email = seller.user.email
    seller_name = seller.store_name
    admin_email(seller_email, seller_name, "REJECTED", reason)

    messages.success(
        request,
        f"Seller '{seller.store_name}' has been rejected!"
        + (f" Reason: {reason}" if reason else ""),
    )
    return redirect("seller_veri")


@login_required
@role_required(allowed_roles=["ADMIN"])
def seller_veri(request):
    unverified = SellerProfile.objects.filter(status="PENDING")
    return render(
        request,
        "admin/seller_veri.html",
        {"unverified": unverified, "active_menu": "verification"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def detailed_view(request, id):
    details = SellerProfile.objects.select_related("user").get(pk=id)
    return render(
        request,
        "admin/details_view.html",
        {"details": details, "active_menu": "verification"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def add_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        slug = slugify(name)
        image = request.FILES.get("image_url")
        description = request.POST.get("des")
        Category.objects.create(
            name=name,
            slug=slug,
            image_url=image,
            description=description,
        )
        messages.success(request, f"Category '{name}' added successfully!")
        return redirect("admin_all_categories")
    return render(request, "admin/add_category.html")
@login_required
@role_required(allowed_roles=["ADMIN"])
def admin_all_categories(request):
    search_query = request.GET.get('search', '')

    categories = Category.objects.prefetch_related("subcategories").order_by("name")

    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(subcategories__name__icontains=search_query)
        ).distinct()

    return render(request, "admin/all_category.html", {
        "categories": categories,
        "active_menu": "category",
        "search_query": search_query
    })

@login_required
@role_required(allowed_roles=["ADMIN"])
def toggle_category_status(request, id):
    if request.method != "POST":
        return redirect("admin_all_categories")
    category = get_object_or_404(Category, id=id)
    category.is_active = not category.is_active
    category.save()
    status_text = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category '{category.name}' has been {status_text}!")
    return redirect("admin_all_categories")

@login_required
@role_required(allowed_roles=["ADMIN"])
def toggle_subcategory_status(request, id):
    if request.method != "POST":
        return redirect("admin_all_categories")
    subcategory = get_object_or_404(SubCategory, id=id)
    subcategory.is_active = not subcategory.is_active
    subcategory.save()
    status_text = "activated" if subcategory.is_active else "deactivated"
    messages.success(
        request, f"Subcategory '{subcategory.name}' has been {status_text}!"
    )
    return redirect("admin_all_categories")


@login_required
@role_required(allowed_roles=["ADMIN"])
def add_subcategory(request):
    from core.models import Category, SubCategory

    if request.method == "POST":
        category_id = request.POST.get("category")
        name = request.POST.get("name")
        if category_id and name:
            category = Category.objects.get(id=category_id)
            SubCategory.objects.create(category=category, name=name)
            messages.success(request, f"Subcategory '{name}' added successfully!")
            return redirect("admin_all_categories")
        else:
            messages.error(request, "Category and name are required.")
    categories = Category.objects.all()
    return render(request, "admin/add_subcategory.html", {"categories": categories})


@login_required
@role_required(allowed_roles=["ADMIN"])
def banner_list(request):
    banners = Banner.objects.order_by("-is_active", "start_date", "-id")
    return render(
        request,
        "admin/banner_list.html",
        {"banners": banners, "active_menu": "banners"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def add_banner(request):
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Banner added successfully.")
            return redirect("admin_banner_list")
    else:
        form = BannerForm()

    return render(
        request,
        "admin/add_banner.html",
        {"form": form, "active_menu": "banners"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def toggle_banner_status(request, id):
    if request.method != "POST":
        return redirect("admin_banner_list")
    banner = get_object_or_404(Banner, id=id)
    banner.is_active = not banner.is_active
    banner.save(update_fields=["is_active"])
    state = "activated" if banner.is_active else "hidden"
    messages.success(request, f"Banner '{banner.title}' has been {state}.")
    return redirect("admin_banner_list")


@login_required
@role_required(allowed_roles=["ADMIN"])
def all_users(request):
    users = User.objects.filter(role="CUSTOMER").order_by("-date_joined")
    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request, "admin/all_users.html", {"page_obj": page_obj, "active_menu": "users"}
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def all_sellers(request):
    sellers = SellerProfile.objects.select_related("user").order_by("-created_at")
    paginator = Paginator(sellers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin/all_sellers.html",
        {"page_obj": page_obj, "active_menu": "sellers"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def approve_product(request):
    products = Product.objects.select_related("seller", "subcategory").filter(
        approval_status="PENDING"
    ).order_by("-created_at")
    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin/approve.html",
        {"page_obj": page_obj, "active_menu": "approve_product"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def approve_single_product(request, id):
    if request.method != "POST":
        return redirect("approve_products")
    product = get_object_or_404(Product, id=id)
    product.approval_status = "APPROVED"
    product.save()
    messages.success(request, f"Product '{product.name}' has been approved!")
    return redirect("approve_products")


@login_required
@role_required(allowed_roles=["ADMIN"])
def reject_single_product(request, id):
    if request.method != "POST":
        return redirect("approve_products")
    product = get_object_or_404(Product, id=id)
    reason = request.POST.get("reason") if request.method == "POST" else None
    product.rejection_reason = reason
    product.approval_status = "REJECTED"
    product.save()
    seller_email = product.seller.user.email
    seller_name = product.seller.store_name
    admin_email(
        seller_email, f"Product '{product.name}' Rejected", "PRODUCT_REJECTED", reason
    )
    messages.success(
        request,
        f"Product '{product.name}' has been rejected!"
        + (f" Reason: {reason}" if reason else ""),
    )
    return redirect("approve_products")


@login_required
@role_required(allowed_roles=["ADMIN"])
def rejected_products(request):
    products = Product.objects.select_related("seller", "subcategory").filter(
        approval_status="REJECTED"
    ).order_by("-created_at")
    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin/rejected_products.html",
        {"page_obj": page_obj, "active_menu": "rejected_products"},
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def rejected_sellers(request):
    sellers = SellerProfile.objects.select_related("user").filter(
        status="REJECTED"
    ).order_by("-created_at")
    paginator = Paginator(sellers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin/rejected_sellers.html",
        {"page_obj": page_obj, "active_menu": "rejected_sellers"},
    )


def _parse_datetime_local(raw_value):
    dt = datetime.fromisoformat(raw_value)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


@login_required
@role_required(allowed_roles=["ADMIN"])
def admin_promo_codes(request):
    if request.method == "POST":
        try:
            scope = (request.POST.get("scope") or "").strip().upper()
            target_id = request.POST.get("target_id")
            coupon_kwargs = {
                "name": (request.POST.get("name") or "").strip(),
                "code": (request.POST.get("code") or "").strip().upper(),
                "discount_type": (request.POST.get("discount_type") or "PERCENT").strip().upper(),
                "discount_value": Decimal(request.POST.get("discount_value") or "0"),
                "valid_from": _parse_datetime_local(request.POST.get("valid_from")),
                "valid_to": _parse_datetime_local(request.POST.get("valid_to")),
                "usage_limit": int(request.POST.get("usage_limit") or 0),
                "min_order_amount": Decimal(request.POST.get("min_order_amount") or "0"),
                "is_active": request.POST.get("is_active") == "on",
            }

            if scope == "CATEGORY":
                coupon_kwargs["category"] = get_object_or_404(Category, id=target_id)
            elif scope == "SUBCATEGORY":
                coupon_kwargs["subcategory"] = get_object_or_404(SubCategory, id=target_id)
            else:
                raise ValidationError("Choose a valid scope.")

            Coupon.objects.create(**coupon_kwargs)
            messages.success(request, "Promo code created successfully.")
            return redirect("admin_promo_codes")
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, "Please enter valid promo code details.")
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))

    promo_codes = Coupon.objects.filter(seller__isnull=True).select_related(
        "category", "subcategory"
    ).order_by("-created_at")
    categories = Category.objects.filter(is_active=True).order_by("name")
    subcategories = SubCategory.objects.filter(is_active=True).select_related(
        "category"
    ).order_by("category__name", "name")
    return render(
        request,
        "admin/promo_codes.html",
        {
            "promo_codes": promo_codes,
            "categories": categories,
            "subcategories": subcategories,
            "category_options": list(categories.values("id", "name")),
            "subcategory_options": list(
                subcategories.values("id", "name", "category__name")
            ),
            "active_menu": "promotions",
        },
    )


@login_required
@role_required(allowed_roles=["ADMIN"])
def toggle_admin_promo_code(request, coupon_id):
    if request.method != "POST":
        return redirect("admin_promo_codes")

    coupon = get_object_or_404(Coupon, id=coupon_id, seller__isnull=True)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=["is_active"])
    state = "activated" if coupon.is_active else "disabled"
    messages.success(request, f"Promo code '{coupon.code}' {state}.")
    return redirect("admin_promo_codes")

