from django.core.management.base import BaseCommand
from easybuy.seller.models import Product, ProductVariant, ProductImage
from django.core.files.base import ContentFile
from PIL import Image
import io
import os

class Command(BaseCommand):
    help = 'Adds real product images'

    def handle(self, *args, **kwargs):
        add_real_images()

def add_real_images():
    print("Adding real product images...")
    
    variants = ProductVariant.objects.all()
    print(f"\nFound {variants.count()} product variants")
    
    # Create images directory if it doesn't exist
    media_root = r"C:\Users\hp\OneDrive\Desktop\BESTBUY\project\images\category"
    products_dir = os.path.join(media_root, "products", "variants")
    os.makedirs(products_dir, exist_ok=True)
    
    colors = [
        (74, 124, 67),    # Primary green
        (255, 127, 80),   # Terracotta
        (14, 165, 233),   # Blue
        (16, 185, 129),   # Emerald
        (245, 158, 11),   # Gold
    ]
    
    for idx, variant in enumerate(variants):
        print(f"\nProcessing: {variant.product.name}")
        
        # Delete existing images
        variant.images.all().delete()
        
        # Create 3 images per variant
        for img_num in range(3):
            # Create a simple colored image
            img = Image.new('RGB', (800, 800), color=colors[idx % len(colors)])
            
            # Add text to image
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Draw product name
            text = f"{variant.product.name}\n{variant.sku_code}"
            draw.text((50, 350), text, fill=(255, 255, 255))
            
            # Save to bytes
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            img_io.seek(0)
            
            # Create ProductImage
            product_image = ProductImage(
                variant=variant,
                alt_text=f"{variant.product.name} - Image {img_num + 1}",
                is_primary=(img_num == 0)
            )
            
            # Save the image file
            filename = f"{variant.sku_code}_img{img_num + 1}.jpg"
            product_image.image.save(filename, ContentFile(img_io.read()), save=True)
            
            print(f"  [OK] Added image {img_num + 1}/3")
    
    print("\n" + "="*50)
    print("IMAGES ADDED SUCCESSFULLY!")
    print("="*50)
    print(f"\nTotal Product Images: {ProductImage.objects.count()}")
    print(f"Images per variant: ~{ProductImage.objects.count() / variants.count():.1f}")
    print("\n" + "="*50)
