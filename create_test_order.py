"""
Create a test PENDING order for testing status changes
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
from easybuy.seller.models import ProductVariant
from django.contrib.auth import get_user_model
from decimal import Decimal
import random
import string
from django.utils import timezone

User = get_user_model()

print("Creating test PENDING order...")
print("=" * 50)

# Get customer1
customer = User.objects.get(username='customer1')

# Get a product variant from seller1
seller1 = User.objects.get(username='seller1')
variant = ProductVariant.objects.filter(product__seller__user=seller1).first()

if not variant:
    print("ERROR: No products found for seller1")
    sys.exit(1)

# Create order
order_number = f"EB{timezone.now().strftime('%Y%m%d')}{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

order = Order.objects.create(
    user=customer,
    order_number=order_number,
    total_amount=Decimal('500.00'),
    payment_status='PENDING',
    order_status='PENDING',  # PENDING status
    shipping_name='akash tomy',
    shipping_phone='9497634775',  # Your WhatsApp number
    shipping_address='Test Address, Mumbai, Maharashtra - 400001'
)

# Create order item
OrderItem.objects.create(
    order=order,
    variant=variant,
    seller=variant.product.seller,
    quantity=1,
    price_at_purchase=variant.selling_price
)

print("\nTest order created successfully!")
print(f"\nOrder Details:")
print(f"Order Number: {order.order_number}")
print(f"Status: {order.order_status}")
print(f"Phone: {order.shipping_phone}")
print(f"Product: {variant.product.name}")
print(f"\nNow:")
print("1. Go to: http://127.0.0.1:8000/seller/orders/")
print("2. Login as seller1 / seller123")
print("3. Find order:", order.order_number)
print("4. Change status from PENDING to SHIPPED")
print("5. Check terminal for debug output")
print("6. Check WhatsApp for message!")
