"""
Debug Shipped Status Issue
"""
import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

from easybuy.user.models import Order
from easybuy.core.whatsapp_utils import whatsapp_notifier
from django.conf import settings

print("Testing SHIPPED Status Notification")
print("=" * 50)

# Get an order
order = Order.objects.filter(shipping_phone='9497634775').order_by('-ordered_at').first()

if not order:
    print("No order found!")
    sys.exit(1)

print(f"Order: {order.order_number}")
print(f"Status: {order.order_status}")
print(f"Phone: {order.shipping_phone}")
print(f"Name: {order.shipping_name}")

print(f"\nWhatsApp Enabled: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")

# Test SHIPPED notification
print("\n" + "=" * 50)
print("Testing SHIPPED Notification...")
print("=" * 50)

try:
    result = whatsapp_notifier.send_order_shipped(order)
    if result:
        print("\nSUCCESS! Shipped notification sent!")
        print("Check your WhatsApp for the message.")
    else:
        print("\nFAILED! Check error above.")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test DELIVERED notification
print("\n" + "=" * 50)
print("Testing DELIVERED Notification...")
print("=" * 50)

try:
    result = whatsapp_notifier.send_order_delivered(order)
    if result:
        print("\nSUCCESS! Delivered notification sent!")
        print("Check your WhatsApp for the message.")
    else:
        print("\nFAILED! Check error above.")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

# Test FEEDBACK notification
print("\n" + "=" * 50)
print("Testing FEEDBACK Notification...")
print("=" * 50)

try:
    result = whatsapp_notifier.send_feedback_request(order)
    if result:
        print("\nSUCCESS! Feedback notification sent!")
        print("Check your WhatsApp for the message.")
    else:
        print("\nFAILED! Check error above.")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Test Complete!")
print("=" * 50)
