from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from easybuy.core.models import Category, User
from easybuy.seller.models import SellerProfile, Product
from easybuy.user.models import OrderItem
from django.db.models import Sum, F
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json

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
        return redirect("all_categories")
    return render(request, "admin/add_category.html")


@login_required
@role_required(allowed_roles=["ADMIN"])
def add_subcategory(request):
    from easybuy.core.models import Category, SubCategory

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
    sellers = SellerProfile.objects.select_related("user").all()
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
    )
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
    product = get_object_or_404(Product, id=id)
    product.approval_status = "APPROVED"
    product.save()
    messages.success(request, f"Product '{product.name}' has been approved!")
    return redirect("approve_products")


@login_required
@role_required(allowed_roles=["ADMIN"])
def reject_single_product(request, id):
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
    )
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
    sellers = SellerProfile.objects.select_related("user").filter(status="REJECTED")
    paginator = Paginator(sellers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "admin/rejected_sellers.html",
        {"page_obj": page_obj, "active_menu": "rejected_sellers"},
    )
