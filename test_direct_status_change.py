"""
Direct test of status change function
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
from easybuy.core.whatsapp_utils import whatsapp_notifier
from django.conf import settings

print("Direct Status Change Test")
print("=" * 50)

# Get the latest PENDING order
order = Order.objects.filter(
    order_number='EB202603130Q4EL3IX',
    order_status='PENDING'
).first()

if not order:
    print("Order not found or not PENDING")
    # Try to find it anyway
    order = Order.objects.filter(order_number='EB202603130Q4EL3IX').first()
    if order:
        print(f"Order found but status is: {order.order_status}")
    else:
        print("Order doesn't exist at all!")
    sys.exit(1)

print(f"Order: {order.order_number}")
print(f"Current Status: {order.order_status}")
print(f"Phone: {order.shipping_phone}")

# Change status to SHIPPED
print("\nChanging status to SHIPPED...")
order.order_status = 'SHIPPED'
order.save()

print(f"New Status: {order.order_status}")

# Send WhatsApp notification
print("\nSending WhatsApp notification...")
if settings.WHATSAPP_NOTIFICATIONS_ENABLED:
    try:
        result = whatsapp_notifier.send_order_shipped(order)
        print(f"Result: {result}")
        if result:
            print("\nSUCCESS! Check your WhatsApp!")
        else:
            print("\nFAILED! Check error above.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("WhatsApp notifications are DISABLED")

print("\n" + "=" * 50)
