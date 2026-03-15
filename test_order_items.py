"""
Test if status change is working
"""
import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

from easybuy.user.models import Order, OrderItem
from easybuy.seller.models import SellerProfile
from django.contrib.auth import get_user_model

User = get_user_model()

print("Checking Order Items for seller1...")
print("=" * 50)

# Get seller1
seller_user = User.objects.get(username='seller1')
seller = seller_user.seller_profile

# Get order items for this seller
order_items = OrderItem.objects.filter(seller=seller).select_related('order')[:5]

print(f"\nFound {order_items.count()} order items for seller1\n")

for item in order_items:
    print(f"OrderItem ID: {item.id}")
    print(f"Order Number: {item.order.order_number}")
    print(f"Status: {item.order.order_status}")
    print(f"Phone: {item.order.shipping_phone}")
    print(f"Product: {item.variant.product.name}")
    print("-" * 50)

print("\nTo test manually:")
print("1. Go to: http://127.0.0.1:8000/seller/orders/")
print("2. Login as seller1 / seller123")
print("3. Find an order with status PENDING or CONFIRMED")
print("4. Change status to SHIPPED")
print("5. Check terminal for debug output")
print("6. Check WhatsApp for message")
