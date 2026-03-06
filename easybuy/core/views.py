from django.shortcuts import render, redirect

from django.contrib.auth import authenticate, login, logout
from .models import Category, User, Address, SubCategory
from django.http import HttpResponse
from easybuy.seller.models import SellerProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from easybuy.seller.models import Product, ProductVariant, ProductImage
from django.core.paginator import Paginator
from easybuy.core.decorators import role_required
from django.db.models import Q


# Create your views here.
@role_required(allowed_roles=["CUSTOMER"])
@login_required
def profile_settings(request):
    if request.method == "POST":
        user = request.user
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
        return redirect("core/profile_settings")

    return render(request, "core/profile.html")


def all_products(request):
    icategory = request.GET.get("category")
    isubCategory = request.GET.get("subcategory")
    ibrand = request.GET.getlist("brand")
    min_price = request.GET.get("min")
    max_price = request.GET.get("max")
    iprod = request.GET.get("q")
    sort = request.GET.get("sort", "newest")
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
    if icategory:
        variants = variants.filter(product__subcategory__category__slug=icategory)
    if isubCategory:
        variants = variants.filter(product__subcategory__slug=isubCategory)
    if ibrand:
        variants = variants.filter(product__brand__in=ibrand)

    if iprod:
        search_query = iprod.strip()
        variants = variants.filter(
            Q(product__name__icontains=search_query)
            | Q(product__description__icontains=search_query)
            | Q(product__brand__icontains=search_query)
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
        Product.objects.filter(
            is_active=True, approval_status="APPROVED", seller__status="APPROVED"
        )
        .values_list("brand", flat=True)
        .distinct()
    )
    categories = Category.objects.filter(is_active=True)
    subcategories = SubCategory.objects.filter(is_active=True)
    variant_list = list(variants)
    variant_ids = [v.id for v in variant_list]
    primary_images = {
        img.variant_id: img
        for img in ProductImage.objects.filter(
            variant_id__in=variant_ids, is_primary=True
        )
    }
    product_data = []
    for variant in variant_list:
        product_data.append(
            {"variant": variant, "image": primary_images.get(variant.id)}
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
    }
    return render(request, "user/all_products.html", context)


def home_view(request):
    categories = Category.objects.filter(is_active=True)
    variants = (
        ProductVariant.objects.filter(product__is_active=True)
        .select_related("product", "product__seller")
        .order_by("-id")[:8]
    )
    variant_ids = [v.id for v in variants]
    primary_images = {
        img.variant_id: img
        for img in ProductImage.objects.filter(
            variant_id__in=variant_ids, is_primary=True
        )
    }
    product_data = []
    for variant in variants:
        product_data.append(
            {"variant": variant, "image": primary_images.get(variant.id)}
        )
    print(f"Product count: {len(product_data)}")
    return render(
        request,
        "core/home.html",
        {"categories": categories, "product_data": product_data},
    )


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if not username or not email or not password1:
            messages.error(request, "All fields are required.")
            return redirect("register")
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
        )
        user.role = "CUSTOMER"
        user.save()
        login(request, user)
        return redirect("home")

    return render(request, "core/register.html")


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
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user).order_by("-is_default", "-id")
    return render(request, "core/addresses.html", {"addresses": addresses})


@login_required
def logout_view(request):
    logout(request)
    return render(request, "core/login.html", {"message": "Logged out successfully!"})


@login_required
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
        "core/profile.html",
        {"addresses": addresses, "default_address": default_address, "user": user},
    )


def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, "core/all_categories.html", {"categories": categories})


def all_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        # print(password)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # print('user')
            login(request, user)
            role = user.role
            if role == "CUSTOMER":
                return redirect("home")
            elif role == "ADMIN":
                user = request.user
                sellers = User.objects.filter(role="SELLER").count()
                users = User.objects.filter(role="CUSTOMER").count()
                return render(
                    request,
                    "admin/admin_dashboard.html",
                    {"sellers": sellers, "users": users},
                )
            elif role == "SELLER":
                user = request.user
                data1 = SellerProfile.objects.get(user=user)
                return render(
                    request, "seller/dashboard.html", {"data1": data1, "user": user}
                )
        else:
            return render(
                request, "core/login.html", {"error": "Invalid username or password"}
            )
    return render(request, "core/login.html")


# def add_sub_category(request):
# if request.method=="POST":
#     data=Category.objects.all()
#     SubCategory.objects.create(
#         category=data,
#         name=request.POST.get('name'),
#         slug=request.POST.get('slug')
#     )
