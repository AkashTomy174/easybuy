from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from .models import SellerProfile, Product
from easybuy.core.models import Category
from .models import Product

User = get_user_model()


def seller_regi_success(request):
    return render(request, "seller/seller_registration_success.html")


def seller_regi(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        store_name = request.POST.get("store_name")
        gst_number = request.POST.get("gst_number")
        pan_number = request.POST.get("pan_number")
        doc = request.FILES.get("doc")
        bank_account_number = request.POST.get("bank_account_number")
        ifsc_code = request.POST.get("ifsc_code")
        business_address = request.POST.get("business_address")
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                role="SELLER",
            )
            SellerProfile.objects.create(
                user=user,
                store_name=store_name,
                store_slug=slugify(store_name),
                gst_number=gst_number,
                pan_number=pan_number,
                doc=doc,
                status="PENDING",
                bank_account_number=bank_account_number,
                ifsc_code=ifsc_code,
                business_address=business_address,
            )
        return redirect("seller_registration_success")
    return render(request, "seller/sellerregistration.html")


@login_required
@role_required(allowed_roles=["SELLER"])
def seller_product_list(request):  # seller product list
    sellers = SellerProfile.objects.prefetch_related("product_set").all()
    return render(request, "seller/inventory.html", {"sellers": sellers})


@login_required
@role_required(allowed_roles=["SELLER"])
def seller_dashboard(request):
    seller = request.user.seller_profile
    products = Product.objects.filter(seller=seller).prefetch_related(
        "variants", "variants__images"
    )
    return render(
        request,
        "seller/dashboard.html",
        {"seller": seller, "products": products, "active_menu": "dashboard"},
    )


@login_required
@role_required(allowed_roles=["SELLER", "ADMIN"])
def seller_inventory(request):
    try:
        seller = request.user.seller_profile
    except SellerProfile.DoesNotExist:
        seller = None
    if seller:
        products = (
            Product.objects.filter(seller=seller, is_active=True)
            .prefetch_related("variants", "variants__images")
            .select_related("subcategory")
            .order_by("-created_at")
        )
        total_inventory_value = 0
        total_stock = 0
        low_stock_count = 0
        out_of_stock_count = 0
        all_variants = []
        for product in products:
            for variant in product.variants.all():
                all_variants.append(variant)
                total_stock += variant.stock_quantity
                total_inventory_value += (
                    float(variant.selling_price) * variant.stock_quantity
                )
                if variant.stock_quantity == 0:
                    out_of_stock_count += 1
                elif variant.stock_quantity <= 10:
                    low_stock_count += 1
    else:
        products = []
        all_variants = []
        total_inventory_value = 1000
        total_stock = 0
        low_stock_count = 0
        out_of_stock_count = 0
    context = {
        "seller": seller,
        "products": products,
        "all_variants": all_variants,
        "total_products": len(products),
        "total_variants": len(all_variants),
        "total_stock": total_stock,
        "total_inventory_value": total_inventory_value,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "active_menu": "inventory",
    }
    return render(request, "seller/inventory.html", context)
