"""
Simple WhatsApp Test Script
"""
import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

from easybuy.core.whatsapp_utils import whatsapp_notifier
from django.conf import settings

print("=" * 60)
print("WhatsApp Test")
print("=" * 60)

print("\nConfiguration:")
print(f"Account SID: {settings.TWILIO_ACCOUNT_SID[:10]}...")
print(f"Auth Token: {settings.TWILIO_AUTH_TOKEN[:10]}...")
print(f"WhatsApp From: {settings.TWILIO_WHATSAPP_FROM}")
print(f"Enabled: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")

if not whatsapp_notifier.client:
    print("\nERROR: Twilio client not initialized!")
    sys.exit(1)

print("\nTwilio client: OK")

print("\nEnter phone number to test (10 digits):")
phone = input("Phone: ").strip()

if phone:
    message = "Test message from EasyBuy! If you received this, WhatsApp integration is working!"
    
    print(f"\nSending to: {phone}")
    
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        formatted_phone = whatsapp_notifier._format_phone(phone)
        print(f"Formatted: {formatted_phone}")
        
        result = client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=formatted_phone
        )
        
        print(f"\nSUCCESS! Message SID: {result.sid}")
        print("Check your WhatsApp!")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("\nCommon issues:")
        print("1. Did you join the sandbox? Send 'join <code>' to +14155238886")
        print("2. Is the phone number correct?")
        print("3. Check Twilio console for errors")
else:
    print("No phone number provided")

print("\n" + "=" * 60)
