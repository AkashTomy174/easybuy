import os
import django
import sys
from pathlib import Path

# Add the easybuy directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'easybuy'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.settings')
django.setup()

from easybuy.user.models import Order, OrderItem

# Find the order
order_number = "EB202603133Q2N03H8"
order = Order.objects.filter(order_number=order_number).first()

if order:
    print(f"Found order: {order.order_number}")
    print(f"Current status: {order.order_status}")
    
    # Reset to PENDING
    order.order_status = 'PENDING'
    order.save()
    
    # Reset all order items to PENDING
    for item in order.items.all():
        item.status = 'PENDING'
        item.save()
    
    print(f"✓ Order reset to PENDING")
    print(f"✓ {order.items.count()} order items reset to PENDING")
    print(f"\nYou can now test status change from PENDING → SHIPPED/DELIVERED")
else:
    print(f"Order {order_number} not found")
