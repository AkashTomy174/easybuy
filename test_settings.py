import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the easybuy directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'easybuy'))

# Load environment variables
load_dotenv()

# Test the boolean conversion
env_value = os.getenv('WHATSAPP_NOTIFICATIONS_ENABLED', 'False')
result = env_value.lower() in ('true', '1', 'yes')

print(f"Environment variable value: {env_value}")
print(f"Converted to boolean: {result}")
print(f"WhatsApp notifications will be: {'ENABLED' if result else 'DISABLED'}")


