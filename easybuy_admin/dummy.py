# dummy_data_admin.py

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import datetime, timedelta
import random

# Import models with correct path
from easybuy.easybuy_admin.models import (
    AdminProfile, Offer, Discount, Coupon,
    OfferDiscountBridge, ProductOfferBridge, CategoryOfferBridge,
    ProductDiscountBridge, CategoryDiscountBridge, PlatformCommission
)
from easybuy.core.models import Category
from easybuy.seller.models import Product, SellerProfile
from easybuy.user.models import OrderItem

User = get_user_model()

print("\n" + "="*60)
print("Creating Dummy Data for easybuy_admin...")
print("="*60 + "\n")

try:
    with transaction.atomic():
        
        # 1. Create AdminProfiles
        print("Creating AdminProfiles...")
        admin = User.objects.filter(username='admin').first()
        if admin:
            admin_profile, created = AdminProfile.objects.get_or_create(
                user=admin,
                defaults={
                    'department': 'Management',
                    'is_active': True
                }
            )
            print("✅ AdminProfile created")
        
        # 2. Create Offers
        print("\nCreating Offers...")
        offers = []
        offer_data = [
            {'title': 'Summer Sale 2024', 'description': 'Get up to 50% off on all summer collection'},
            {'title': 'Diwali Special', 'description': 'Biggest festival sale of the year'},
            {'title': 'New Year Offer', 'description': 'Start the new year with amazing deals'},
            {'title': 'Flash Sale', 'description': '24-hour flash sale - Limited time only'},
            {'title': 'Weekend Special', 'description': 'Exclusive weekend deals'},
        ]
        
        for data in offer_data:
            offer, created = Offer.objects.get_or_create(
                title=data['title'],
                defaults={
                    **data,
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=30),
                    'is_active': True
                }
            )
            offers.append(offer)
        print(f"✅ {len(offers)} Offers created")
        
        # 3. Create Discounts
        print("\nCreating Discounts...")
        discounts = []
        discount_data = [
            {'name': '10% Off', 'discount_type': 'PERCENT', 'discount_value': 10.00},
            {'name': '20% Off', 'discount_type': 'PERCENT', 'discount_value': 20.00},
            {'name': '30% Off', 'discount_type': 'PERCENT', 'discount_value': 30.00},
            {'name': '50% Off', 'discount_type': 'PERCENT', 'discount_value': 50.00},
            {'name': 'Flat ₹100 Off', 'discount_type': 'FLAT', 'discount_value': 100.00},
            {'name': 'Flat ₹200 Off', 'discount_type': 'FLAT', 'discount_value': 200.00},
            {'name': 'Flat ₹500 Off', 'discount_type': 'FLAT', 'discount_value': 500.00},
            {'name': 'Flat ₹1000 Off', 'discount_type': 'FLAT', 'discount_value': 1000.00},
        ]
        
        for data in discount_data:
            discount, created = Discount.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            discounts.append(discount)
        print(f"✅ {len(discounts)} Discounts created")
        
        # 4. Create Coupons
        print("\nCreating Coupons...")
        coupon_codes = ['SAVE10', 'SAVE20', 'SAVE50', 'FIRST100', 'WELCOME50', 'FLAT200']
        
        for code in coupon_codes:
            Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'discount_value': random.choice([100, 200, 500, 1000]),
                    'valid_from': datetime.now(),
                    'valid_to': datetime.now() + timedelta(days=90),
                    'usage_limit': random.randint(10, 100),
                    'used_count': random.randint(0, 10)
                }
            )
        print(f"✅ {len(coupon_codes)} Coupons created")
        
        # 5. Create Offer-Discount Bridges
        print("\nCreating Offer-Discount Bridges...")
        for offer in offers[:3]:
            for discount in random.sample(discounts, k=min(3, len(discounts))):
                OfferDiscountBridge.objects.get_or_create(
                    offer=offer,
                    discount=discount
                )
        print("✅ Offer-Discount Bridges created")
        
        # 6. Create Product-Discount Bridges
        print("\nCreating Product-Discount Bridges...")
        products = list(Product.objects.all()[:10])
        if products:
            for product in products:
                for discount in random.sample(discounts, k=min(2, len(discounts))):
                    ProductDiscountBridge.objects.get_or_create(
                        product=product,
                        discount=discount
                    )
            print(f"✅ Product-Discount Bridges created for {len(products)} products")
        else:
            print("⚠️ No products found - skipping Product-Discount Bridges")
        
        # 7. Create Category-Discount Bridges
        print("\nCreating Category-Discount Bridges...")
        categories = list(Category.objects.all()[:5])
        if categories:
            for category in categories:
                for discount in random.sample(discounts, k=min(2, len(discounts))):
                    CategoryDiscountBridge.objects.get_or_create(
                        category=category,
                        discount=discount
                    )
            print(f"✅ Category-Discount Bridges created for {len(categories)} categories")
        
        # 8. Create Product-Offer Bridges
        print("\nCreating Product-Offer Bridges...")
        if products:
            for product in products:
                for offer in random.sample(offers, k=min(2, len(offers))):
                    ProductOfferBridge.objects.get_or_create(
                        product=product,
                        offer=offer
                    )
            print(f"✅ Product-Offer Bridges created for {len(products)} products")
        
        # 9. Create Category-Offer Bridges
        print("\nCreating Category-Offer Bridges...")
        if categories:
            for category in categories:
                for offer in random.sample(offers, k=min(2, len(offers))):
                    CategoryOfferBridge.objects.get_or_create(
                        category=category,
                        offer=offer
                    )
            print(f"✅ Category-Offer Bridges created for {len(categories)} categories")
        
        # 10. Create Platform Commissions
        print("\nCreating Platform Commissions...")
        sellers = list(SellerProfile.objects.all()[:5])
        order_items = list(OrderItem.objects.all()[:10])
        
        if sellers and order_items:
            for order_item in order_items:
                seller = random.choice(sellers)
                commission_percentage = random.uniform(5, 20)
                commission_amount = order_item.price * order_item.quantity * (commission_percentage / 100)
                
                PlatformCommission.objects.get_or_create(
                    seller=seller,
                    order_item=order_item,
                    defaults={
                        'commission_percentage': commission_percentage,
                        'commission_amount': commission_amount,
                        'settlement_status': random.choice(['PENDING', 'SETTLED']),
                        'settled_at': datetime.now() if random.choice([True, False]) else None
                    }
                )
            print(f"✅ Platform Commissions created for {len(order_items)} order items")
        else:
            print("⚠️ No sellers or order items found - skipping Platform Commissions")
        
        print("\n" + "="*60)
        print("🎉 All easybuy_admin dummy data created successfully!")
        print("="*60)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()