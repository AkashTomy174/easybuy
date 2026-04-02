from django.core.management.base import BaseCommand
from easybuy.seller.models import Product, ProductVariant, ProductImage
import os
from django.conf import settings
import urllib.request
import ssl


class Command(BaseCommand):
    help = "Download and add product images based on product names"

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        image_folder = "products/variants"
        image_dir = os.path.join(media_root, image_folder)

        # Create directory if it doesn't exist
        os.makedirs(image_dir, exist_ok=True)

        # Define image URLs - using reliable Unsplash source
        # Each product type gets appropriate images
        image_downloads = [
            # Mobile Phones
            {
                "keywords": ["iphone", "mobile", "phone", "galaxy", "smartphone"],
                "images": [
                    (
                        "smartphone_1.jpg",
                        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&h=600&fit=crop",
                    ),
                    (
                        "smartphone_2.jpg",
                        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Laptops
            {
                "keywords": ["laptop", "macbook", "notebook", "computer"],
                "images": [
                    (
                        "laptop_1.jpg",
                        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&h=600&fit=crop",
                    ),
                    (
                        "laptop_2.jpg",
                        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # TVs
            {
                "keywords": ["tv", "television", "oled", "smart tv", "55 inch"],
                "images": [
                    (
                        "tv_1.jpg",
                        "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=600&h=600&fit=crop",
                    ),
                    (
                        "tv_2.jpg",
                        "https://images.unsplash.com/photo-1461151304267-38535e780c79?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Headphones
            {
                "keywords": [
                    "sony",
                    "headphone",
                    "headset",
                    "earphone",
                    "wh-1000xm5",
                    "audio",
                ],
                "images": [
                    (
                        "headphones_1.jpg",
                        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop",
                    ),
                    (
                        "headphones_2.jpg",
                        "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Nike Shoes
            {
                "keywords": ["nike", "air max", "sneaker", "shoe"],
                "images": [
                    (
                        "nike_shoes_1.jpg",
                        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=600&fit=crop",
                    ),
                    (
                        "nike_shoes_2.jpg",
                        "https://images.unsplash.com/photo-1600185365926-3a2ce3cdb9eb?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Adidas
            {
                "keywords": ["adidas", "track pants", "sportswear", "pants"],
                "images": [
                    (
                        "adidas_clothing_1.jpg",
                        "https://images.unsplash.com/photo-1556906781-9a412961c28c?w=600&h=600&fit=crop",
                    ),
                    (
                        "adidas_clothing_2.jpg",
                        "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Furniture
            {
                "keywords": ["wooden", "table", "dining", "furniture"],
                "images": [
                    (
                        "wooden_table_1.jpg",
                        "https://images.unsplash.com/photo-1611269154421-4e27233ac5c7?w=600&h=600&fit=crop",
                    ),
                    (
                        "wooden_table_2.jpg",
                        "https://images.unsplash.com/photo-1577140917170-285929fb55b7?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Books
            {
                "keywords": ["python", "book", "programming", "techbook"],
                "images": [
                    (
                        "programming_book_1.jpg",
                        "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&h=600&fit=crop",
                    ),
                    (
                        "programming_book_2.jpg",
                        "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&h=600&fit=crop",
                    ),
                ],
            },
            # Mouse/Accessories
            {
                "keywords": ["mouse", "wireless", "logitech", "accessory"],
                "images": [
                    (
                        "wireless_mouse_1.jpg",
                        "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&h=600&fit=crop",
                    ),
                    (
                        "wireless_mouse_2.jpg",
                        "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&h=600&fit=crop",
                    ),
                ],
            },
        ]

        # Create SSL context to avoid certificate issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Download images
        self.stdout.write("Downloading product images...")

        for category in image_downloads:
            for filename, url in category["images"]:
                filepath = os.path.join(image_dir, filename)
                if not os.path.exists(filepath):
                    try:
                        self.stdout.write(f"Downloading {filename}...")
                        opener = urllib.request.build_opener()
                        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
                        urllib.request.install_opener(opener)
                        urllib.request.urlretrieve(url, filepath)
                        self.stdout.write(self.style.SUCCESS(f"Downloaded {filename}"))
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to download {filename}: {e}")
                        )
                        # Try with urllib directly
                        try:
                            req = urllib.request.Request(
                                url, headers={"User-Agent": "Mozilla/5.0"}
                            )
                            with urllib.request.urlopen(
                                req, context=ssl_context
                            ) as response:
                                with open(filepath, "wb") as f:
                                    f.write(response.read())
                            self.stdout.write(
                                self.style.SUCCESS(f"Downloaded {filename} (retry)")
                            )
                        except Exception as e2:
                            self.stdout.write(
                                self.style.ERROR(f"Retry also failed: {e2}")
                            )
                else:
                    self.stdout.write(f"Skipping {filename} (already exists)")

        # Now assign images to variants based on product name
        variants = ProductVariant.objects.all()
        images_added = 0

        for variant in variants:
            # Clear existing images
            variant.images.all().delete()

            product_name = (variant.product.name + " " + variant.product.brand).lower()

            # Find matching category based on keywords
            matched_category = None
            for category in image_downloads:
                for keyword in category["keywords"]:
                    if keyword in product_name:
                        matched_category = category
                        break
                if matched_category:
                    break

            # If no match, use first category as default
            if not matched_category:
                matched_category = image_downloads[0]

            # Get images from matched category
            category_images = [img[0] for img in matched_category["images"]]

            # Add images to variant
            for idx, image_name in enumerate(category_images):
                image_path = f"{image_folder}/{image_name}"
                full_path = os.path.join(image_dir, image_name)

                if os.path.exists(full_path):
                    ProductImage.objects.create(
                        variant=variant,
                        image=image_path,
                        is_primary=(idx == 0),
                    )
                    images_added += 1
                    self.stdout.write(
                        f"Added {image_name} to {variant.product.name} - {variant.sku_code}"
                    )
                else:
                    self.stdout.write(f"Image not found: {full_path}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully added {images_added} product images")
        )
