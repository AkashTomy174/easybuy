from decimal import Decimal
import uuid

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.models import Address, Notification, User
from seller.models import Product, ProductVariant, SellerProfile
from core.models import Category, SubCategory
from user.models import Cart, CartItem, Wishlist, WishlistItem


class Command(BaseCommand):
    help = "Measure cold vs warm query counts for cache-backed pages."

    def handle(self, *args, **options):
        fixture = self._ensure_fixture_data()
        public_client = Client()
        auth_client = Client()
        auth_client.force_login(fixture["customer"])

        routes = [
            ("Login", reverse("all_login"), public_client),
            ("Home", reverse("home"), public_client),
            ("All Products", reverse("all_products"), public_client),
            ("Filtering", reverse("filtering"), public_client),
            ("Profile Settings", reverse("profile_settings"), auth_client),
            ("Payment Methods", reverse("payment_methods"), auth_client),
        ]

        results = []
        total_cold = 0
        total_warm = 0

        self.stdout.write("")
        self.stdout.write(f"Cache backend: {cache.__class__.__name__}")
        self.stdout.write("Measuring DB queries with cold cache vs warm cache")
        self.stdout.write("")

        for label, path, client in routes:
            try:
                cache.clear()
            except Exception:
                pass

            cold_queries = self._query_count(client, path)
            warm_queries = self._query_count(client, path)
            saved_queries = max(cold_queries - warm_queries, 0)
            reduction_pct = (saved_queries / cold_queries * 100) if cold_queries else 0

            total_cold += cold_queries
            total_warm += warm_queries
            results.append(
                {
                    "label": label,
                    "cold": cold_queries,
                    "warm": warm_queries,
                    "saved": saved_queries,
                    "reduction_pct": reduction_pct,
                }
            )

            self.stdout.write(
                f"{label}: cold={cold_queries}, warm={warm_queries}, "
                f"saved={saved_queries}, reduction={reduction_pct:.1f}%"
            )

        total_saved = max(total_cold - total_warm, 0)
        overall_pct = (total_saved / total_cold * 100) if total_cold else 0

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Overall sampled reduction: {overall_pct:.1f}% "
                f"({total_cold} -> {total_warm} queries)"
            )
        )
        self.stdout.write(
            "Note: this is a sampled page-level average for the current dataset and cache backend."
        )

    def _query_count(self, client, path):
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path, HTTP_HOST="localhost")
            if hasattr(response, "render"):
                response.render()
        return len(queries)

    def _ensure_fixture_data(self):
        customer, _ = User.objects.get_or_create(
            username="cacheprobe_customer",
            defaults={
                "email": "cacheprobe_customer@example.com",
                "role": User.ROLE_CUSTOMER,
                "is_active": True,
            },
        )
        if not customer.check_password("testpass123"):
            customer.set_password("testpass123")
            customer.role = User.ROLE_CUSTOMER
            customer.is_active = True
            customer.email = customer.email or "cacheprobe_customer@example.com"
            customer.save()

        seller_user, _ = User.objects.get_or_create(
            username="cacheprobe_seller",
            defaults={
                "email": "cacheprobe_seller@example.com",
                "role": User.ROLE_SELLER,
                "is_active": True,
            },
        )
        if not seller_user.check_password("testpass123"):
            seller_user.set_password("testpass123")
            seller_user.role = User.ROLE_SELLER
            seller_user.is_active = True
            seller_user.email = seller_user.email or "cacheprobe_seller@example.com"
            seller_user.save()

        seller_profile, created = SellerProfile.objects.get_or_create(
            user=seller_user,
            defaults={
                "store_name": "Cache Probe Store",
                "store_slug": f"cache-probe-store-{uuid.uuid4().hex[:6]}",
                "gst_number": "32ABCDE1234F1Z5",
                "pan_number": "ABCDE1234F",
                "bank_account_number": "123456789012",
                "doc": SimpleUploadedFile(
                    "cacheprobe-doc.txt",
                    b"cache probe verification document",
                    content_type="text/plain",
                ),
                "ifsc_code": "TEST0001234",
                "business_address": "Cache Probe Business Address",
                "status": SellerProfile.STATUS_APPROVED,
            },
        )
        if not created and seller_profile.status != SellerProfile.STATUS_APPROVED:
            seller_profile.status = SellerProfile.STATUS_APPROVED
            seller_profile.save(update_fields=["status"])

        category, _ = Category.objects.get_or_create(
            slug="cache-probe-category",
            defaults={
                "name": "Cache Probe Category",
                "description": "Cache measurement category",
                "is_active": True,
            },
        )
        subcategory, _ = SubCategory.objects.get_or_create(
            slug="cache-probe-subcategory",
            defaults={
                "category": category,
                "name": "Cache Probe Subcategory",
                "is_active": True,
            },
        )
        if subcategory.category_id != category.id:
            subcategory.category = category
            subcategory.save(update_fields=["category"])

        product, _ = Product.objects.get_or_create(
            slug="cache-probe-product",
            defaults={
                "seller": seller_profile,
                "subcategory": subcategory,
                "name": "Cache Probe Product",
                "description": "Product used for cache measurement",
                "brand": "EasyBuy",
                "model_number": "CACHE-PROBE-001",
                "approval_status": Product.APPROVAL_APPROVED,
                "is_active": True,
            },
        )
        update_fields = []
        if product.seller_id != seller_profile.id:
            product.seller = seller_profile
            update_fields.append("seller")
        if product.subcategory_id != subcategory.id:
            product.subcategory = subcategory
            update_fields.append("subcategory")
        if product.approval_status != Product.APPROVAL_APPROVED:
            product.approval_status = Product.APPROVAL_APPROVED
            update_fields.append("approval_status")
        if not product.is_active:
            product.is_active = True
            update_fields.append("is_active")
        if update_fields:
            product.save(update_fields=update_fields)

        variant, _ = ProductVariant.objects.get_or_create(
            sku_code="CACHEPROBE001",
            defaults={
                "product": product,
                "mrp": Decimal("1999.00"),
                "selling_price": Decimal("1499.00"),
                "cost_price": Decimal("999.00"),
                "stock_quantity": 10,
                "tax_percentage": 18,
            },
        )
        if variant.product_id != product.id:
            variant.product = product
            variant.save(update_fields=["product"])

        Address.objects.get_or_create(
            user=customer,
            house_info="123 Cache Street",
            defaults={
                "full_name": "Cache Probe User",
                "phone_number": "9876543210",
                "pincode": "682001",
                "locality": "Cache Locality",
                "city": "Kochi",
                "state": "Kerala",
                "country": "India",
                "address_type": "HOME",
                "is_default": True,
            },
        )

        cart, _ = Cart.objects.get_or_create(user=customer)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={
                "quantity": 1,
                "price_at_time": variant.selling_price,
            },
        )
        if created:
            cart.total_amount = variant.selling_price
            cart.save(update_fields=["total_amount"])

        wishlist, _ = Wishlist.objects.get_or_create(
            user=customer,
            wishlist_name="My Wishlist",
        )
        WishlistItem.objects.get_or_create(wishlist=wishlist, variant=variant)

        Notification.objects.get_or_create(
            user=customer,
            title="Cache Probe Notification",
            defaults={
                "type": "info",
                "message": "Notification used for cache measurement",
            },
        )

        return {"customer": customer}
