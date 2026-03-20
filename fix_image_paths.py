#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")
django.setup()
from easybuy.seller.models import ProductImage

count = 0
for img in ProductImage.objects.all():
    old_path = img.image.name
    # Strip leading media/ or media\\
    new_path = old_path.lstrip("media/").lstrip("media\\").lstrip("/")
    if old_path != new_path:
        img.image.name = new_path
        img.image.field.generate_filename = (
            lambda instance, filename: new_path
        )  # Force save
        img.save()
        print(f"Fixed: {old_path} → {new_path}")
        count += 1
print(f"Total fixed: {count}")
