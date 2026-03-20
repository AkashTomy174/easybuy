#!/usr/bin/env python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")
import django

django.setup()
from easybuy.seller.models import ProductImage

count = 0
for img in ProductImage.objects.all():
    old = img.image.name
    new = old.replace("\\", "/")
    if old != new:
        img.image.name = new
        img.save()
        print(f"Fixed \\ → / : {old} → {new}")
        count += 1
print(f"Total backslash fixes: {count}")
