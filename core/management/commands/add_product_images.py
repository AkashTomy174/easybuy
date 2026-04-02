from django.core.management.base import BaseCommand
from easybuy.seller.models import Product, ProductVariant, ProductImage
import os
from django.conf import settings


class Command(BaseCommand):
    help = "Add product images based on product names"

    def handle(self, *args, **options):
        # Define image mappings based on product name keywords
        image_mappings = {
            "tv": ["tv1.jpg", "tv2.jpg"],
            "samsung": ["tv1.jpg", "tv2.jpg", "Screenshot_1.png"],
            "iphone": ["Screenshot_1.png"],
            "apple": ["Screenshot_1.png"],
            "macbook": ["Screenshot_1.png"],
            "sony": ["Screenshot_1.png"],
            "nike": ["Screenshot_1.png"],
            "adidas": ["Screenshot_1.png"],
            "wooden": ["Screenshot_1.png"],
            "python": ["Screenshot_1.png"],
            "book": ["Screenshot_1.png"],
            "mouse": ["Screenshot_1.png"],
            "wireless": ["Screenshot_1.png"],
            "oled": ["tv1.jpg", "tv2.jpg"],
        }

        media_root = settings.MEDIA_ROOT
        image_folder = "products/variants"

        variants = ProductVariant.objects.all()
        images_added = 0

        for variant in variants:
            # Check if variant already has images
            if variant.images.exists():
                self.stdout.write(
                    f"Skipping {variant.product.name} - {variant.sku_code} (already has images)"
                )
                continue

            product_name = variant.product.name.lower()

            # Find matching images based on keywords
            matched_images = []
            for keyword, images in image_mappings.items():
                if keyword in product_name:
                    matched_images = images
                    break

            if not matched_images:
                matched_images = ["Screenshot_1.png"]

            # Add images to variant
            for idx, image_name in enumerate(matched_images):
                image_path = os.path.join(media_root, image_folder, image_name)
                if os.path.exists(image_path):
                    ProductImage.objects.create(
                        variant=variant,
                        image=f"{image_folder}/{image_name}",
                        is_primary=(idx == 0),
                    )
                    images_added += 1
                    self.stdout.write(
                        f"Added {image_name} to {variant.product.name} - {variant.sku_code}"
                    )
                else:
                    self.stdout.write(f"Image not found: {image_path}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully added {images_added} product images")
        )
