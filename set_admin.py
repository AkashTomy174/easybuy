#!/usr/bin/env python3
"""
Set admin user: username='admin', password='921967', role='ADMIN', is_superuser=True
Idempotent - safe to run anytime.
"""

import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
django.setup()

from easybuy.core.models import User

def set_admin():
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@easybuy.com',
            'role': 'ADMIN',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    
    # Always set password (updates if exists)
    admin.set_password('921967')
    admin.role = 'ADMIN'
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    
    status = "created" if created else "updated"
    print(f"✅ Admin user '{admin.username}' ({status})")
    print(f"   Role: ADMIN")
    print(f"   Password: 921967")
    print(f"   Superuser: Yes")
    print("\nLogin: http://127.0.0.1:8000/admin/")

if __name__ == "__main__":
    set_admin()

