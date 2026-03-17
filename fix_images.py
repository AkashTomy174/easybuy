from django.conf import settings
from django.core.management.base import BaseCommand
from easybuy.seller.models import ProductImage
import os


class Command(BaseCommand):
    def handle(self, *args, **options):
        count = 0
        for img in ProductImage.objects.all():
            old_path = img.image.name
            new_path = old_path.lstrip("media/").lstrip("media\\")
            if old_path != new_path:
                img.image.name = new_path
                img.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Fixed: {old_path} → {new_path}"))
        self.stdout.write(self.style.SUCCESS(f"Total fixed: {count} paths"))
