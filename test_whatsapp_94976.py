import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")
import django

django.setup()

from easybuy.core.whatsapp_utils import whatsapp_notifier
from django.conf import settings

print("=" * 60)
print("WhatsApp Test: 9497634775")
print("=" * 60)

print("Configuration:")
print("Account SID:", bool(settings.TWILIO_ACCOUNT_SID))
print("Auth Token:", bool(settings.TWILIO_AUTH_TOKEN))
print("From:", settings.TWILIO_WHATSAPP_FROM)
print("Client:", whatsapp_notifier.client is not None)

phone = "9497634775"
message = "EasyBuy Test Message to 9497634775! Order notifications working. Check Twilio logs after sandbox join."

print(f"\nSending to: {phone}")
print("Formatted: whatsapp:+919497634775")

result = whatsapp_notifier.send_message(phone, message)
print(f"Result: {result}")

print("\n" + "=" * 60)
print("Check WhatsApp 9497634775 & Twilio logs!")
print('Join sandbox first: send "join <code>" to +14155238886')
