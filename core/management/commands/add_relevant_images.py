from django.core.management.base import BaseCommand
from easybuy.seller.models import Product, ProductVariant, ProductImage
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io
import os

class Command(BaseCommand):
    help = 'Adds relevant product images based on category'

    def handle(self, *args, **kwargs):
        add_relevant_images()

def add_relevant_images():
    print("Adding relevant product images based on categories...")
    
    variants = ProductVariant.objects.select_related('product', 'product__subcategory').all()
    print(f"\nFound {variants.count()} product variants")
    
    # Create images directory
    media_root = r"C:\Users\hp\OneDrive\Desktop\BESTBUY\project\images\category"
    products_dir = os.path.join(media_root, "products", "variants")
    os.makedirs(products_dir, exist_ok=True)
    
    # Color schemes based on category
    category_colors = {
        'Electronics': {
            'Smartphones': [(30, 30, 35), (50, 50, 60), (20, 20, 25)],
            'Laptops': [(40, 40, 50), (60, 60, 70), (80, 80, 90)],
            'Tablets': [(45, 45, 55), (65, 65, 75), (85, 85, 95)],
            'Headphones': [(20, 20, 25), (40, 40, 45), (60, 60, 65)],
            'Cameras': [(35, 35, 40), (55, 55, 60), (75, 75, 80)],
            'Smart Watches': [(25, 25, 30), (45, 45, 50), (65, 65, 70)],
        },
        'Fashion': {
            'Men\'s Clothing': [(70, 90, 120), (100, 120, 150), (130, 150, 180)],
            'Women\'s Clothing': [(200, 100, 120), (220, 120, 140), (240, 140, 160)],
            'Shoes': [(80, 60, 40), (100, 80, 60), (120, 100, 80)],
            'Accessories': [(180, 140, 100), (200, 160, 120), (220, 180, 140)],
            'Watches': [(50, 50, 50), (70, 70, 70), (90, 90, 90)],
        },
        'Home & Kitchen': {
            'Furniture': [(139, 90, 60), (159, 110, 80), (179, 130, 100)],
            'Kitchen Appliances': [(200, 200, 200), (220, 220, 220), (240, 240, 240)],
            'Home Decor': [(160, 120, 80), (180, 140, 100), (200, 160, 120)],
            'Bedding': [(220, 200, 180), (240, 220, 200), (255, 240, 220)],
            'Storage': [(100, 100, 120), (120, 120, 140), (140, 140, 160)],
        },
        'Sports & Fitness': {
            'Gym Equipment': [(60, 60, 60), (80, 80, 80), (100, 100, 100)],
            'Sports Wear': [(0, 100, 200), (20, 120, 220), (40, 140, 240)],
            'Yoga & Fitness': [(100, 180, 100), (120, 200, 120), (140, 220, 140)],
            'Outdoor Sports': [(200, 100, 0), (220, 120, 20), (240, 140, 40)],
            'Cycling': [(255, 100, 0), (255, 120, 20), (255, 140, 40)],
        },
        'Books & Media': {
            'Fiction': [(139, 69, 19), (159, 89, 39), (179, 109, 59)],
            'Non-Fiction': [(70, 130, 180), (90, 150, 200), (110, 170, 220)],
            'Educational': [(34, 139, 34), (54, 159, 54), (74, 179, 74)],
            'Comics': [(255, 165, 0), (255, 185, 20), (255, 205, 40)],
            'Magazines': [(220, 20, 60), (240, 40, 80), (255, 60, 100)],
        },
        'Beauty & Personal Care': {
            'Skincare': [(255, 192, 203), (255, 212, 223), (255, 232, 243)],
            'Makeup': [(255, 105, 180), (255, 125, 200), (255, 145, 220)],
            'Haircare': [(138, 43, 226), (158, 63, 246), (178, 83, 255)],
            'Fragrances': [(186, 85, 211), (206, 105, 231), (226, 125, 251)],
        }
    }
    
    # Default colors
    default_colors = [(74, 124, 67), (94, 144, 87), (114, 164, 107)]
    
    for idx, variant in enumerate(variants):
        product = variant.product
        subcategory_name = product.subcategory.name if product.subcategory else 'Unknown'
        category_name = product.subcategory.category.name if product.subcategory and product.subcategory.category else 'Unknown'
        
        print(f"\n{idx + 1}. Processing: {product.name}")
        print(f"   Category: {category_name} > {subcategory_name}")
        
        # Delete existing images
        variant.images.all().delete()
        
        # Get color scheme for this category
        colors = default_colors
        if category_name in category_colors and subcategory_name in category_colors[category_name]:
            colors = category_colors[category_name][subcategory_name]
        
        # Create 3 images per variant with different angles/views
        image_styles = [
            {'label': 'Front View', 'color_idx': 0, 'text_y': 350},
            {'label': 'Side View', 'color_idx': 1, 'text_y': 370},
            {'label': 'Detail View', 'color_idx': 2, 'text_y': 390},
        ]
        
        for img_num, style in enumerate(image_styles):
            # Create image with category-specific color
            color = colors[style['color_idx']]
            img = Image.new('RGB', (800, 800), color=color)
            draw = ImageDraw.Draw(img)
            
            # Add gradient effect
            for y in range(800):
                alpha = y / 800
                gradient_color = tuple(int(c * (1 - alpha * 0.3)) for c in color)
                draw.line([(0, y), (800, y)], fill=gradient_color)
            
            # Add product info text
            try:
                # Try to use a better font if available
                font_large = ImageFont.truetype("arial.ttf", 40)
                font_medium = ImageFont.truetype("arial.ttf", 28)
                font_small = ImageFont.truetype("arial.ttf", 20)
            except:
                # Fallback to default font
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Draw product name (wrapped)
            product_name = product.name
            if len(product_name) > 30:
                words = product_name.split()
                line1 = ' '.join(words[:len(words)//2])
                line2 = ' '.join(words[len(words)//2:])
                draw.text((50, 300), line1, fill=(255, 255, 255), font=font_large)
                draw.text((50, 350), line2, fill=(255, 255, 255), font=font_large)
            else:
                draw.text((50, 320), product_name, fill=(255, 255, 255), font=font_large)
            
            # Draw brand
            brand_text = f"Brand: {product.brand}"
            draw.text((50, 420), brand_text, fill=(255, 255, 255, 200), font=font_medium)
            
            # Draw SKU
            sku_text = f"SKU: {variant.sku_code}"
            draw.text((50, 460), sku_text, fill=(255, 255, 255, 180), font=font_small)
            
            # Draw price
            price_text = f"₹{variant.selling_price}"
            draw.text((50, 500), price_text, fill=(255, 255, 255), font=font_large)
            
            # Draw category badge
            badge_text = f"{category_name} > {subcategory_name}"
            draw.text((50, 50), badge_text, fill=(255, 255, 255, 220), font=font_small)
            
            # Draw view label
            draw.text((50, 750), style['label'], fill=(255, 255, 255, 180), font=font_small)
            
            # Add decorative elements based on category
            if 'Electronics' in category_name:
                # Draw circuit-like pattern
                draw.rectangle([650, 50, 750, 150], outline=(255, 255, 255, 100), width=3)
                draw.line([(650, 100), (750, 100)], fill=(255, 255, 255, 100), width=2)
                draw.line([(700, 50), (700, 150)], fill=(255, 255, 255, 100), width=2)
            elif 'Fashion' in category_name:
                # Draw fashion icon
                draw.ellipse([650, 50, 750, 150], outline=(255, 255, 255, 100), width=3)
            elif 'Books' in category_name:
                # Draw book icon
                draw.rectangle([660, 60, 740, 140], outline=(255, 255, 255, 100), width=3)
                draw.line([(700, 60), (700, 140)], fill=(255, 255, 255, 100), width=2)
            
            # Save to bytes
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=90)
            img_io.seek(0)
            
            # Create ProductImage
            product_image = ProductImage(
                variant=variant,
                alt_text=f"{product.name} - {style['label']}",
                is_primary=(img_num == 0)
            )
            
            # Save the image file
            filename = f"{variant.sku_code}_img{img_num + 1}.jpg"
            product_image.image.save(filename, ContentFile(img_io.read()), save=True)
            
            print(f"   [OK] Added {style['label']}")
    
    print("\n" + "="*60)
    print("RELEVANT IMAGES ADDED SUCCESSFULLY!")
    print("="*60)
    print(f"\nTotal Product Images: {ProductImage.objects.count()}")
    print(f"Images per variant: ~{ProductImage.objects.count() / variants.count():.1f}")
    print("\nImages are now category-specific with:")
    print("  - Color schemes matching product categories")
    print("  - Product name, brand, SKU, and price")
    print("  - Category badges")
    print("  - Multiple views (Front, Side, Detail)")
    print("\n" + "="*60)
