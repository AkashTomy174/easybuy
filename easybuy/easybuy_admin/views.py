from easybuy.core.models import Category, User
from easybuy.seller.models import SellerProfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.text import slugify
from django.core.paginator import Paginator
from .models import Category
from easybuy.core.decorators import role_required
from django.contrib.auth.decorators import login_required


from django.shortcuts import render, get_object_or_404, redirect


@login_required
@role_required(allowed_roles=["ADMIN"])
def approve_seller(request, id):
    seller = get_object_or_404(SellerProfile, id=id)
    seller.status = "APPROVED"
    seller.save()
    return redirect("seller_veri")


@login_required
@role_required(allowed_roles=["ADMIN"])
def reject_seller(request, id):
    seller = get_object_or_404(SellerProfile, id=id)
    seller.status = "REJECTED"
    seller.save()
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
