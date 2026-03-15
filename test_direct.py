"""
Direct WhatsApp Test
"""
import os
import sys
from pathlib import Path

project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

from django.conf import settings
from twilio.rest import Client

print("Testing WhatsApp to: 9497634775")
print("-" * 40)

# Initialize Twilio client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# Format phone number
phone = "9497634775"
formatted_phone = f"whatsapp:+91{phone}"

print(f"From: {settings.TWILIO_WHATSAPP_FROM}")
print(f"To: {formatted_phone}")

# Test message
message = """
Test message from EasyBuy!

If you received this, your WhatsApp integration is working correctly!

- EasyBuy Team
"""

try:
    print("\nSending message...")
    result = client.messages.create(
        body=message,
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=formatted_phone
    )
    
    print(f"\nSUCCESS!")
    print(f"Message SID: {result.sid}")
    print(f"Status: {result.status}")
    print("\nCheck your WhatsApp - you should receive the message!")
    
except Exception as e:
    print(f"\nERROR: {str(e)}")
    print("\nPossible reasons:")
    print("1. Phone number 9497634775 not joined to sandbox")
    print("2. Twilio credentials incorrect")
    print("3. Twilio account issue")
    
    print("\nTo fix:")
    print("1. From phone 9497634775, send WhatsApp message:")
    print("   To: +1 415 523 8886")
    print("   Message: join <your-code>")
    print("2. Wait for confirmation")
    print("3. Run this test again")
