from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.text import slugify
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from easybuy.core.decorators import role_required
from .models import SellerProfile, Product, ProductVariant, ProductImage, InventoryLog
from easybuy.core.models import SubCategory
from easybuy.user.models import Order, OrderItem, Review
from easybuy.core.whatsapp_utils import whatsapp_notifier

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
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    import json
    
    seller = request.user.seller_profile
    now = timezone.now()
    
    # Get all order items for this seller
    all_order_items = OrderItem.objects.filter(seller=seller).select_related("order", "variant__product")
    
    # Key Metrics
    total_orders = all_order_items.count()
    total_revenue = sum(float(item.price_at_purchase * item.quantity) for item in all_order_items)
    pending_orders = all_order_items.filter(order__order_status="PENDING").count()
    
    # Products stats
    total_products = Product.objects.filter(seller=seller).count()
    active_products = Product.objects.filter(seller=seller, is_active=True).count()
    
    # Average order value
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Revenue by status
    delivered_revenue = sum(float(item.price_at_purchase * item.quantity) 
                           for item in all_order_items.filter(order__order_status="DELIVERED"))
    pending_revenue = sum(float(item.price_at_purchase * item.quantity) 
                         for item in all_order_items.filter(order__order_status="PENDING"))
    
    # Last 7 days revenue data for chart
    daily_revenue = []
    daily_labels = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_orders = all_order_items.filter(
            order__ordered_at__gte=day_start,
            order__ordered_at__lt=day_end
        )
        day_revenue = sum(float(item.price_at_purchase * item.quantity) for item in day_orders)
        
        daily_revenue.append(day_revenue)
        daily_labels.append(date.strftime("%b %d"))
    
    # Top 5 selling products
    top_products = (
        all_order_items
        .values('variant__product__name')
        .annotate(total_sold=Sum('quantity'), revenue=Sum(F('price_at_purchase') * F('quantity')))
        .order_by('-total_sold')[:5]
    )
    
    # Order status distribution
    status_counts = {
        'PENDING': all_order_items.filter(order__order_status='PENDING').count(),
        'SHIPPED': all_order_items.filter(order__order_status='SHIPPED').count(),
        'DELIVERED': all_order_items.filter(order__order_status='DELIVERED').count(),
        'CANCELLED': all_order_items.filter(order__order_status='CANCELLED').count(),
    }
    
    # Recent orders (last 5)
    recent_orders = all_order_items.order_by('-order__ordered_at')[:5]
    
    # Low stock alerts
    low_stock_items = ProductVariant.objects.filter(
        product__seller=seller,
        stock_quantity__lte=10,
        stock_quantity__gt=0
    ).select_related('product')[:5]
    
    context = {
        "seller": seller,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "total_products": total_products,
        "active_products": active_products,
        "average_order_value": average_order_value,
        "delivered_revenue": delivered_revenue,
        "pending_revenue": pending_revenue,
        "daily_revenue_data": json.dumps(daily_revenue),
        "daily_labels_data": json.dumps(daily_labels),
        "top_products": top_products,
        "status_counts": status_counts,
        "recent_orders": recent_orders,
        "low_stock_items": low_stock_items,
        "active_menu": "dashboard",
    }
    return render(request, "seller/dashboard.html", context)


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

        paginator = Paginator(products, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        products = []
        all_items = []
        total_inventory_value = 1000
        total_stock = 0
        low_stock_count = 0
        out_of_stock_count = 0
        page_obj = None
    context = {
        "seller": seller,
        "page_obj": page_obj,
        "all_items": all_items,
        "total_products": len(products) if seller else 0,
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
            item = ProductVariant.objects.create(
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

            item_id = request.POST.get("variant_id")
            stock_to_add = int(request.POST.get("stock_amount", 0))
            reason = request.POST.get("reason", "Manual stock addition")

            if stock_to_add <= 0:
                return JsonResponse({"success": False, "error": "Invalid stock amount"})
            item = ProductVariant.objects.select_related("product").get(
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
        except ProductVariant.DoesNotExist:
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
    status_filter = request.GET.get('status')
    page = request.GET.get('page', 1)
    
    base_query = OrderItem.objects.filter(seller=seller).select_related("order", "variant", "variant__product").annotate(
        subtotal=F("price_at_purchase") * F("quantity")
    )
    
    if status_filter:
        base_query = base_query.filter(order__order_status=status_filter)
   
    paginator = Paginator(base_query, 8)
    order_items = paginator.get_page(page)
    
    all_query = OrderItem.objects.filter(seller=seller).select_related("order", "variant", "variant__product")
    total_orders = all_query.count()
    total_revenue = sum(item.price_at_purchase * item.quantity for item in all_query)
    
    pending_orders = OrderItem.objects.filter(seller=seller, order__order_status="PENDING").count()
    shipped_orders = OrderItem.objects.filter(seller=seller, order__order_status="SHIPPED").count()
    delivered_orders = OrderItem.objects.filter(seller=seller, order__order_status="DELIVERED").count()
    cancelled_orders = OrderItem.objects.filter(seller=seller, order__order_status="CANCELLED").count()

    context = {
        "order_items": order_items,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "shipped_orders": shipped_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "current_status_filter": status_filter,
        "active_menu": "orders",
    }

    return render(request, "seller/orders.html", context)


@login_required
@role_required(allowed_roles=["SELLER"])
def status(request, id):
    import logging
    logger = logging.getLogger(__name__)
    
    # Also write to a file for debugging
    with open('status_change_log.txt', 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"Status change request received\n")
        f.write(f"Time: {timezone.now()}\n")
        f.write(f"User: {request.user.username}\n")
        f.write(f"OrderItem ID: {id}\n")
    
    seller = request.user.seller_profile
    order_item = get_object_or_404(OrderItem, seller=seller, id=id)

    new_status = request.POST.get("status")
    
    with open('status_change_log.txt', 'a') as f:
        f.write(f"New Status: {new_status}\n")
        f.write(f"Order: {order_item.order.order_number}\n")
        f.write(f"Old Status: {order_item.order.order_status}\n")
        f.write(f"Phone: {order_item.order.shipping_phone}\n")
    
    if new_status:
        old_status = order_item.order.order_status
        
        print(f"\n=== ORDER STATUS CHANGE ===")
        print(f"Order: {order_item.order.order_number}")
        print(f"Old Status: {old_status}")
        print(f"New Status: {new_status}")
        print(f"Phone: {order_item.order.shipping_phone}")
        print(f"WhatsApp Enabled: {getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False)}")
        
        # Update the main Order status
        order_item.order.order_status = new_status
        order_item.order.save()
        
        # Also update the OrderItem status to keep them in sync
        order_item.status = new_status
        order_item.save()
        
        with open('status_change_log.txt', 'a') as f:
            f.write(f"Status updated in database\n")
            f.write(f"WhatsApp Enabled: {getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False)}\n")
        
        # Send WhatsApp notification based on status
        if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
            print(f"Attempting to send WhatsApp notification...")
            with open('status_change_log.txt', 'a') as f:
                f.write(f"Attempting WhatsApp notification...\n")
            try:
                if new_status == "SHIPPED":
                    print("Sending SHIPPED notification...")
                    result = whatsapp_notifier.send_order_shipped(order_item.order)
                    print(f"SHIPPED notification result: {result}")
                    with open('status_change_log.txt', 'a') as f:
                        f.write(f"SHIPPED notification sent: {result}\n")
                elif new_status == "DELIVERED":
                    print("Sending DELIVERED notification...")
                    result1 = whatsapp_notifier.send_order_delivered(order_item.order)
                    print(f"DELIVERED notification result: {result1}")
                    with open('status_change_log.txt', 'a') as f:
                        f.write(f"DELIVERED notification sent: {result1}\n")
                    # Send feedback request
                    print("Sending FEEDBACK notification...")
                    result2 = whatsapp_notifier.send_feedback_request(order_item.order)
                    print(f"FEEDBACK notification result: {result2}")
                    with open('status_change_log.txt', 'a') as f:
                        f.write(f"FEEDBACK notification sent: {result2}\n")
                elif new_status == "CANCELLED":
                    print("Sending CANCELLED notification...")
                    result = whatsapp_notifier.send_order_cancelled(order_item.order)
                    print(f"CANCELLED notification result: {result}")
                    with open('status_change_log.txt', 'a') as f:
                        f.write(f"CANCELLED notification sent: {result}\n")
                print("WhatsApp notification process completed")
            except Exception as e:
                print(f"ERROR sending WhatsApp: {str(e)}")
                with open('status_change_log.txt', 'a') as f:
                    f.write(f"ERROR: {str(e)}\n")
                import traceback
                traceback.print_exc()
        else:
            print("WhatsApp notifications are DISABLED")
            with open('status_change_log.txt', 'a') as f:
                f.write(f"WhatsApp notifications DISABLED\n")
        
        print(f"=== END STATUS CHANGE ===\n")
        
        messages.success(request, f"Order status updated to {new_status}")

    return redirect("seller_orders")


@login_required
@role_required(allowed_roles=["SELLER"])
def seller_reviews(request):
    seller = request.user.seller_profile
    
    reviews = (
        Review.objects
        .filter(product__seller=seller)
        .select_related("user", "product")
        .order_by("-created_at")
    )
    
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "active_menu": "reviews",
    }
    
    return render(request, "seller/reviews.html", context)


@login_required
@role_required(allowed_roles=["SELLER"])
def reply_review(request, review_id):
    seller = request.user.seller_profile
    review = get_object_or_404(
        Review.objects.select_related("product"),
        id=review_id,
        product__seller=seller
    )
    
    if request.method == "POST":
        reply = request.POST.get("reply", "").strip()
        
        if not reply:
            messages.error(request, "Reply cannot be empty.")
            return redirect("seller_reviews")
        
        review.seller_reply = reply
        review.replied_at = timezone.now()
        review.save()
        
        messages.success(request, "Reply posted successfully!")
        return redirect("seller_reviews")
    
    return redirect("seller_reviews")


# ============================================
# SELLER REVIEW REPLY
# ============================================

from easybuy.user.models import Review
from django.utils import timezone

@login_required
@role_required(allowed_roles=["SELLER"])
def reply_to_review(request, review_id):
    """Allow seller to reply to a review"""
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=400)
    
    review = get_object_or_404(Review.objects.select_related('product__seller'), id=review_id)
    
    # Check if the review is for seller's product
    if review.product.seller.user != request.user:
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)
    
    reply = request.POST.get("reply", "").strip()
    
    if not reply:
        return JsonResponse({"success": False, "message": "Reply cannot be empty"})
    
    if len(reply) > 500:
        return JsonResponse({"success": False, "message": "Reply too long (max 500 characters)"})
    
    review.seller_reply = reply
    review.replied_at = timezone.now()
    review.save()
    
    return JsonResponse({
        "success": True,
        "message": "Reply posted successfully",
        "reply": reply,
        "replied_at": review.replied_at.strftime("%B %d, %Y")
    })
