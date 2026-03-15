"""
Test script to verify Twilio WhatsApp integration
Run this to test if your credentials and setup are working
"""
import os
import sys
from pathlib import Path

# Add project to path
project_path = Path(__file__).resolve().parent
sys.path.insert(0, str(project_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
import django
django.setup()

from easybuy.core.whatsapp_utils import whatsapp_notifier
from django.conf import settings

print("=" * 60)
print("WhatsApp Integration Test")
print("=" * 60)

# Check configuration
print("\n1. Checking Configuration...")
print(f"   TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID[:10]}..." if settings.TWILIO_ACCOUNT_SID else "   TWILIO_ACCOUNT_SID: NOT SET")
print(f"   TWILIO_AUTH_TOKEN: {settings.TWILIO_AUTH_TOKEN[:10]}..." if settings.TWILIO_AUTH_TOKEN else "   TWILIO_AUTH_TOKEN: NOT SET")
print(f"   TWILIO_WHATSAPP_FROM: {settings.TWILIO_WHATSAPP_FROM}")
print(f"   WHATSAPP_NOTIFICATIONS_ENABLED: {settings.WHATSAPP_NOTIFICATIONS_ENABLED}")

if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
    print("\n❌ ERROR: Twilio credentials not configured!")
    print("   Please update your .env file with correct credentials.")
    sys.exit(1)

if not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
    print("\n⚠️  WARNING: WhatsApp notifications are DISABLED")
    print("   Set WHATSAPP_NOTIFICATIONS_ENABLED=True in .env")
    sys.exit(1)

print("   ✅ Configuration looks good!")

# Check Twilio client
print("\n2. Checking Twilio Client...")
if whatsapp_notifier.client:
    print("   ✅ Twilio client initialized successfully!")
else:
    print("   ❌ ERROR: Twilio client failed to initialize")
    sys.exit(1)

# Test phone number formatting
print("\n3. Testing Phone Number Formatting...")
test_numbers = ["9876543210", "919876543210", "+919876543210"]
for num in test_numbers:
    formatted = whatsapp_notifier._format_phone(num)
    print(f"   {num} → {formatted}")

# Send test message
print("\n4. Sending Test Message...")
print("   Enter the phone number to test (10 digits, e.g., 9876543210):")
phone = input("   Phone: ").strip()

if not phone:
    print("   ⚠️  No phone number provided. Skipping test message.")
else:
    test_message = """
🧪 *Test Message from EasyBuy*

Hi! This is a test message to verify your WhatsApp integration is working correctly.

If you received this message, your setup is successful! ✅

- EasyBuy Team
    """.strip()
    
    print(f"\n   Sending test message to: {phone}")
    print("   Please wait...")
    
    try:
        success = whatsapp_notifier.send_message(phone, test_message)
        
        if success:
            print("\n   ✅ SUCCESS! Message sent successfully!")
            print("   Check your WhatsApp - you should receive the test message.")
        else:
            print("\n   ❌ FAILED! Message could not be sent.")
            print("   Check the error logs above.")
    except Exception as e:
        print(f"\n   ❌ ERROR: {str(e)}")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)

print("\n📋 Troubleshooting Checklist:")
print("   [ ] Twilio Account SID is correct (starts with AC)")
print("   [ ] Twilio Auth Token is correct (32 characters)")
print("   [ ] You joined WhatsApp sandbox (sent 'join <code>')")
print("   [ ] Phone number is correct (10 digits)")
print("   [ ] WHATSAPP_NOTIFICATIONS_ENABLED=True in .env")
print("   [ ] Django server was restarted after .env changes")

print("\n💡 Common Issues:")
print("   - 'Not a valid WhatsApp number' → Join sandbox first")
print("   - 'Authentication failed' → Check Account SID and Auth Token")
print("   - 'Permission denied' → Check Twilio account status")
print("   - No message received → Check phone number format")

print("\n📚 For more help, see: WHATSAPP_INTEGRATION_GUIDE.md")
print()
