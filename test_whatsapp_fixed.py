import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")
import django

django.setup()

from easybuy.core.whatsapp_utils import whatsapp_notifier
from easybuy.user.models import Order
from django.conf import settings

print("=" * 60)
print("WhatsApp Order Notification Test")
print("=" * 60)

print("\nConfiguration:")
print("TWILIO_ACCOUNT_SID:", bool(settings.TWILIO_ACCOUNT_SID))
print("Auth Token:", bool(settings.TWILIO_AUTH_TOKEN))
print("WhatsApp From:", settings.TWILIO_WHATSAPP_FROM)
print("Notifications Enabled:", settings.WHATSAPP_NOTIFICATIONS_ENABLED)
print("Client Ready:", whatsapp_notifier.client is not None)

order = Order.objects.first()
if not order:
    print("No orders found!")
    sys.exit(1)

print("\nTest Order:", order.order_number)
print("Phone:", order.shipping_phone)

print("\nTesting Order Shipped...")
result1 = whatsapp_notifier.send_order_shipped(order)
print("Shipped:", result1)

print("\nTesting Order Delivered...")
result2 = whatsapp_notifier.send_order_delivered(order)
print("Delivered:", result2)

print("\nTesting Feedback Request...")
result3 = whatsapp_notifier.send_feedback_request(order)
print("Feedback:", result3)

print("\n" + "=" * 60)
print("Test complete! Check your WhatsApp.")
