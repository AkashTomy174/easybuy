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
print("WhatsApp Order Notification Test - FIXED VERSION")
print("=" * 60)

print("\nConfiguration:")
print(f"TWILIO_ACCOUNT_SID: {'✅' if settings.TWILIO_ACCOUNT_SID else '❌'}")
print(f"Auth Token: {'✅' if settings.TWILIO_AUTH_TOKEN else '❌'}")
print(f"WhatsApp From: {settings.TWILIO_WHATSAPP_FROM}")
print(f"Notifications Enabled: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")
print(f"Client Ready: {'✅' if whatsapp_notifier.client else '❌'}")

# Find test order
order = Order.objects.first()
if not order:
    print("❌ No orders found! Run populate_db.py first.")
    sys.exit(1)

print(f"\nTest Order: {order.order_number}")
print(f"Phone: {order.shipping_phone}")

# Test notifications
tests = [
    ("Order Shipped", whatsapp_notifier.send_order_shipped),
    ("Order Delivered", whatsapp_notifier.send_order_delivered),
    ("Feedback Request", whatsapp_notifier.send_feedback_request),
]

for name, func in tests:
    print(f"\nTesting {name}... ", end="")
    result = func(order)
    print(f"{'✅' if result else '❌'}")

print("\n" + "=" * 60)
print("Test complete! Check WhatsApp and Twilio console.")
print("Note: Sandbox requires 'join <code>' from test phone.")
