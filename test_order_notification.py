"""
Test Order Notification
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

print("Testing Order Notification")
print("-" * 40)

# Get the latest order
order = Order.objects.filter(shipping_phone='9497634775').order_by('-ordered_at').first()

if not order:
    print("No order found with phone 9497634775")
    sys.exit(1)

print(f"Order Number: {order.order_number}")
print(f"Phone: {order.shipping_phone}")
print(f"Amount: {order.total_amount}")
print(f"Status: {order.order_status}")
print(f"Name: {order.shipping_name}")

print(f"\nWhatsApp Enabled: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")

if settings.WHATSAPP_NOTIFICATIONS_ENABLED:
    print("\nSending order confirmation...")
    try:
        result = whatsapp_notifier.send_order_confirmation(order)
        if result:
            print("SUCCESS! Check your WhatsApp!")
        else:
            print("FAILED! Check logs above.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
else:
    print("\nWhatsApp notifications are DISABLED")
    print("Set WHATSAPP_NOTIFICATIONS_ENABLED=True in .env")
