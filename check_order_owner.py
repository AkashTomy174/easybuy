"""
Check if seller1 owns the test order
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
from django.contrib.auth import get_user_model

User = get_user_model()

print("Checking test order ownership...")
print("=" * 50)

# Get the test order
order = Order.objects.filter(order_number='EB20260313HWXUX5R1').first()

if not order:
    print("ERROR: Test order not found!")
    print("Run: python create_test_order.py")
    sys.exit(1)

print(f"Order: {order.order_number}")
print(f"Status: {order.order_status}")
print(f"Phone: {order.shipping_phone}")

# Get order items
order_items = OrderItem.objects.filter(order=order)
print(f"\nOrder Items: {order_items.count()}")

for item in order_items:
    print(f"\nOrderItem ID: {item.id}")
    print(f"Product: {item.variant.product.name}")
    print(f"Seller: {item.seller.user.username}")
    print(f"Seller Store: {item.seller.store_name}")
    
    # Check if seller1 owns this
    seller1 = User.objects.get(username='seller1')
    if item.seller.user == seller1:
        print(">>> This item belongs to seller1 - CORRECT!")
        print(f"\nTo update status:")
        print(f"URL: http://127.0.0.1:8000/seller/status/{item.id}/")
        print(f"Method: POST")
        print(f"Data: status=SHIPPED")
    else:
        print(f">>> ERROR: This item belongs to {item.seller.user.username}, not seller1!")

print("\n" + "=" * 50)
print("Make sure you're logged in as: seller1 / seller123")
print("=" * 50)
