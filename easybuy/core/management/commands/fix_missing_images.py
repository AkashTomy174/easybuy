from django.core.management.base import BaseCommand
from django.conf import settings
from easybuy.seller.models import ProductImage
import os
import shutil
from pathlib import Path
import random


class Command(BaseCommand):
    help = "Fix ProductImage paths and create missing files using existing generics"

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        variants_dir = media_root / "products" / "variants"
        variants_dir.mkdir(parents=True, exist_ok=True)

        # List available generics
        self.stdout.write(
            f'Available jpgs in {variants_dir}: {[p.name for p in variants_dir.glob("*.jpg")]}'
        )
        generic_paths = list(variants_dir.glob("*.jpg"))
        if not generic_paths:
            self.stdout.write(self.style.ERROR("No generic jpg images found!"))
            return

        fixed_paths = 0
        created_files = 0

        for pi in ProductImage.objects.all():
            if pi.image.name:
                # Fix Windows backslashes to forward slashes
                old_name = pi.image.name
                new_name = old_name.replace("\\\\", "/")
                if old_name != new_name:
                    pi.image.name = new_name
                    pi.save()
                    fixed_paths += 1
                    self.stdout.write(f"Fixed path: {old_name} → {new_name}")

                # Check if file exists
                img_path = variants_dir / new_name
                if not img_path.exists():
                    try:
                        src = random.choice(generic_paths)
                        img_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, img_path)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created {img_path.name} from {src.name}"
                            )
                        )
                        created_files += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Failed to copy for {img_path.name}: {e}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Fixed {fixed_paths} paths and created {created_files} missing images!"
            )
        )
