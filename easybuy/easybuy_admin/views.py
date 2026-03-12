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

@login_required
@role_required(allowed_roles=["ADMIN"])
def admin_dashboard(request):
    user = request.user
    sellers = User.objects.filter(role="SELLER").count()
    users = User.objects.filter(role="CUSTOMER").count()
    return render(
        request,
        "admin/admin_dashboard.html",
        {"sellers": sellers, "users": users},
    )


def admin_email(email, seller_name, status):
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

We regret to inform you that your seller account application has been rejected.
Please contact support for more information.

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
    seller.status = "REJECTED"
    seller.save()
    seller_email = seller.user.email
    seller_name = seller.store_name
    admin_email(seller_email, seller_name, "REJECTED")

    messages.success(request, f"Seller '{seller.store_name}' has been rejected!")
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
    return render(request, "add_category.html")


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
    product.approval_status = "REJECTED"
    product.save()
    messages.success(request, f"Product '{product.name}' has been rejected!")
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
