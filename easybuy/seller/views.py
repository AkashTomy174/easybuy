# trunk-ignore-all(isort)
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from .models import SellerProfile, Product
from easybuy.core.models import Category, SubCategory
from .models import Product, ProductVariant, ProductImage
from django.db import transaction

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
def seller_product_list(request):
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
    seller = request.user.seller_profile
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


# class Product(models.Model):
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="products")
#     subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="products")
#     name = models.CharField(max_length=255)
#     slug = models.SlugField()
#     description = models.TextField()
#     brand = models.CharField(max_length=100)
#     model_number = models.CharField(max_length=100)
#     is_cancellable = models.BooleanField(default=True)
#     is_returnable = models.BooleanField(default=True)
#     return_days = models.IntegerField(default=7)
#     approval_status = models.CharField(max_length=20, default='PENDING')
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     def __str__(self):
#         return self.name


# class ProductVariant(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
#     sku_code = models.CharField(max_length=100, unique=True)
#     mrp = models.DecimalField(max_digits=10, decimal_places=2)
#     selling_price = models.DecimalField(max_digits=10, decimal_places=2)
#     cost_price = models.DecimalField(max_digits=10, decimal_places=2)
#     stock_quantity = models.IntegerField()
#     weight = request.POST.get('sku')
#     length = request.POST.get('sku')
#     width = request.POST.get('sku')
#     height = request.POST.get('sku')
#     tax_percentage = models.FloatField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     def __str__(self):
#         return f"{self.product.name} - {self.sku_code}"


# class ProductImage(models.Model):
#     variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
#     image = models.ImageField(upload_to='products/variants/',null=True, blank=True)
#     alt_text = models.CharField(max_length=255, blank=True)
#     is_primary = models.BooleanField(default=False)
#     def __str__(self):
#         return f"{self.variant.sku_code} Image"


@login_required
@role_required(allowed_roles="SELLER")
def add_product(request):
    if request.method == "POST":
        with transaction.atomic():
            subcategory_id = request.POST.get("subcategory")
            subcategory_obj = SubCategory.objects.get(id=subcategory_id)
            # slug will be auto-generated by the model's save() method
            product = Product.objects.create(
                seller=request.user.seller_profile,
                subcategory=subcategory_obj,
                name=request.POST.get("name"),
                description=request.POST.get("des"),
                brand=request.POST.get("brand"),
                model_number=request.POST.get("model"),
                is_cancellable=True if request.POST.get("cancellable") else False,
                is_returnable=True if request.POST.get("returnable") else False,
                is_active=request.POST.get("is_active")
                != "on",  # Default True, False only when explicitly unchecked
                return_days=(
                    int(request.POST.get("return"))
                    if request.POST.get("returnable")
                    else 0
                ),
            )
            variant = ProductVariant.objects.create(
                product=product,
                sku_code=request.POST.get("sku"),
                mrp=request.POST.get("mrp"),
                selling_price=request.POST.get("price"),
                cost_price=request.POST.get("cost"),
                stock_quantity=request.POST.get("stock"),
                weight=request.POST.get("weight"),
                length=request.POST.get("length"),
                width=request.POST.get("width"),
                height=request.POST.get("height"),
                tax_percentage=request.POST.get("tax"),
            )
            images = request.FILES.getlist("images")
            for idx, img in enumerate(images):
                ProductImage.objects.create(
                    variant=variant,
                    image=img,
                    is_primary=(idx == 0),  # First image is set as primary
                )

        return redirect("seller_products_list")

    subcategories = SubCategory.objects.filter(is_active=True).select_related(
        "category"
    )
    return render(
        request,
        "seller/add_product.html",
        {"subcategories": subcategories, "active_menu": "add_product"},
    )
