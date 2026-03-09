# trunk-ignore-all(isort)
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from easybuy.core.decorators import role_required
from .models import SellerProfile, Product, ProductVariant, ProductImage, InventoryLog
from .models import ProductVariant as Productitem
from easybuy.core.models import Category, SubCategory
from .models import Product, ProductImage, InventoryLog
from django.db import transaction
from easybuy.user.models import Order, OrderItem
from django.shortcuts import get_object_or_404

User = get_user_model()


def seller_regi_success(request):
    return render(request, "seller/seller_registration_success.html")


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
            Product.objects.filter(seller=seller)
            .prefetch_related("variants", "variants__images")
            .select_related("subcategory")
            .order_by("-created_at")
        )
        total_inventory_value = 0
        total_stock = 0
        low_stock_count = 0
        out_of_stock_count = 0
        all_items = []
        for product in products:
            for item in product.variants.all():
                all_items.append(item)
                total_stock += item.stock_quantity
                total_inventory_value += float(item.selling_price) * item.stock_quantity
                if item.stock_quantity == 0:
                    out_of_stock_count += 1
                elif item.stock_quantity <= 10:
                    low_stock_count += 1
    else:
        products = []
        all_items = []
        total_inventory_value = 1000
        total_stock = 0
        low_stock_count = 0
        out_of_stock_count = 0
    context = {
        "seller": seller,
        "products": products,
        "all_items": all_items,
        "total_products": len(products),
        "total_variants": len(all_items),
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


# class Productitem(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="items")
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
#     item = models.ForeignKey(Productitem, on_delete=models.CASCADE, related_name="images")
#     image = models.ImageField(upload_to='products/items/',null=True, blank=True)
#     alt_text = models.CharField(max_length=255, blank=True)
#     is_primary = models.BooleanField(default=False)
#     def __str__(self):
#         return f"{self.item.sku_code} Image"


@login_required
@role_required(allowed_roles="SELLER")
def add_product(request):
    if request.method == "POST":
        with transaction.atomic():
            subcategory_id = request.POST.get("subcategory")
            subcategory_obj = SubCategory.objects.get(id=subcategory_id)
            product = Product.objects.create(
                seller=request.user.seller_profile,
                subcategory=subcategory_obj,
                name=request.POST.get("name"),
                description=request.POST.get("des"),
                brand=request.POST.get("brand"),
                model_number=request.POST.get("model"),
                is_cancellable=True if request.POST.get("cancellable") else False,
                is_returnable=True if request.POST.get("returnable") else False,
                is_active=request.POST.get("is_active") != "on",
                return_days=(
                    int(request.POST.get("return"))
                    if request.POST.get("returnable")
                    else 0
                ),
            )
            item = Productitem.objects.create(
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
                    variant=item,
                    image=img,
                    is_primary=(idx == 0),
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


@login_required
@role_required(allowed_roles=["SELLER"])
def add_stock(request):
    if request.method == "POST":
        try:
            item_id = request.POST.get("item_id")
            stock_to_add = int(request.POST.get("stock_amount", 0))
            reason = request.POST.get("reason", "Manual stock addition")

            if stock_to_add <= 0:
                return JsonResponse({"success": False, "error": "Invalid stock amount"})
            item = Productitem.objects.select_related("product").get(
                id=item_id, product__seller=request.user.seller_profile
            )

            item.stock_quantity += stock_to_add
            item.save()
            InventoryLog.objects.create(
                variant=item,
                change_amount=stock_to_add,
                reason=reason,
                performed_by=request.user,
            )

            return JsonResponse(
                {
                    "success": True,
                    "new_stock": item.stock_quantity,
                    "message": f"Successfully added {stock_to_add} units",
                }
            )
        except Productitem.DoesNotExist:
            return JsonResponse({"success": False, "error": "item not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})


@login_required
@role_required(allowed_roles=["SELLER"])
def deactivate(request, id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    try:
        item = Productitem.objects.select_related("product").get(
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

    except Productitem.DoesNotExist:
        return JsonResponse({"success": False, "error": "item not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    # class Order(models.Model):


#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
#     order_number = models.CharField(max_length=100, unique=True)
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_status = models.CharField(max_length=20)
#     order_status = models.CharField(max_length=20)
#     shipping_name = models.CharField(max_length=100, null=True, blank=True)
#     shipping_phone = models.CharField(max_length=15, null=True, blank=True)
#     shipping_address = models.TextField(null=True, blank=True)
#     ordered_at = models.DateTimeField(auto_now_add=True)


# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     item = models.ForeignKey(Productitem, on_delete=models.CASCADE)
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
#     quantity = models.IntegerField()
#     price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)


@login_required
@role_required(allowed_roles=["SELLER"])
def seller_order(request):
    seller = request.user.seller_profile
    order_items = (
        OrderItem.objects.filter(seller=seller)
        .select_related("order", "variant", "variant__product")
        .annotate(subtotal=F("price_at_purchase") * F("quantity"))
        .order_by("-order__ordered_at")
    )
    total_orders = order_items.count()
    total_revenue = sum(
        float(item.price_at_purchase * item.quantity) for item in order_items
    )
    pending_orders = order_items.filter(order__order_status="PENDING").count()
    shipped_orders = order_items.filter(order__order_status="SHIPPED").count()
    cancelled_orders = order_items.filter(order__order_status="CANCELLED").count()

    context = {
        "order_items": order_items,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "shipped_orders": shipped_orders,
        "cancelled_orders": cancelled_orders,
        "active_menu": "orders",
    }

    return render(request, "seller/orders.html", context)


@login_required
@role_required(allowed_roles=["SELLER"])
def status(request, id):

    seller = request.user.seller_profile
    order_item = get_object_or_404(OrderItem, seller=seller, id=id)

    status = request.POST.get("status")
    if status:
        order_item.order.order_status = status
        order_item.order.save()

    return redirect("seller_orders")
