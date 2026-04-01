import requests, decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify
from easybuy.seller.models import SellerProfile, Product, ProductVariant, ProductImage
from easybuy.core.models import SubCategory, User
from easybuy.core.models import SubCategory, Category

class Command(BaseCommand):
    help = 'Search Amazon via Rainforest and save to DB'

    def add_arguments(self, parser):
        parser.add_argument('keyword', type=str)

    def handle(self, *args, **options):
        API_KEY = "YOUR_API_KEY_HERE"  # <--- Paste your key here
        keyword = options['keyword']
        
        # 1. Setup default seller and category (Adjust IDs as needed)
        seller = SellerProfile.objects.first() 
        subcat = SubCategory.objects.first()
        if not seller:
            self.stdout.write(self.style.ERROR("No seller found. Please run populate_db first."))
            return

        # Ensure we have a generic category for imports
        category, _ = Category.objects.get_or_create(name="Imported", defaults={'slug': 'imported'})
        subcat, _ = SubCategory.objects.get_or_create(name="Amazon Items", category=category, defaults={'slug': 'amazon-items'})

        # 2. Call Rainforest Search API
        params = {
            'api_key': API_KEY,
            'type': 'search',
            'amazon_domain': 'amazon.in',
            'search_term': keyword
        }
        
        # ... inside your handle function ...
        response = requests.get('https://api.rainforestapi.com', params=params)
        res = response.json()
        self.stdout.write(f"Searching for {keyword}...")
        try:
            response = requests.get('https://api.rainforestapi.com/request', params=params)
            res = response.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Network error: {e}"))
            return

        if 'search_results' not in res:
            self.stdout.write(self.style.ERROR(f"API Error: {res.get('request_info', {}).get('message', 'Unknown error')}"))
            msg = res.get('request_info', {}).get('message', 'Unknown error')
            self.stdout.write(self.style.ERROR(f"API Error: {msg}"))
            return

        for item in res.get('search_results', []):
            # ... rest of your code ...
        
        self.stdout.write(f"Searching for {keyword}...")
        res = requests.get('https://api.rainforestapi.com', params=params).json()


        for item in res.get('search_results', [])[:10]: # Top 10 items
            asin = item.get('asin')
            title = item.get('title')
            
            if not title or not asin:
                continue
            
            # 3. Create Product
            product, created = Product.objects.get_or_create(
                model_number=asin,
                name=title[:255],
                defaults={
                    'seller': seller,
                    'subcategory': subcat,
                    'name': item.get('title')[:255],
                    'slug': slugify(title[:50] + "-" + asin),
                    'model_number': asin,
                    'brand': item.get('brand', 'Generic'),
                    'description': f"Rating: {item.get('rating')} stars",
                    'approval_status': 'APPROVED'
                    'description': f"Imported from Amazon. Rating: {item.get('rating', 'N/A')} stars.",
                    'approval_status': 'APPROVED',
                    'is_active': True
                }
            )

            # 4. Create Variant (Handling Price)
            price_data = item.get('price', {})
            raw_price = price_data.get('value', 0)
            price = decimal.Decimal(str(raw_price)) if raw_price else decimal.Decimal('0.00')
            
            # If price is missing, generate a random realistic one
            if not raw_price:
                import random
                price = decimal.Decimal(random.randint(500, 5000))
            else:
                price = decimal.Decimal(str(raw_price))

            variant, v_created = ProductVariant.objects.get_or_create(
                product=product,
                sku_code=f"AMZ-{asin}",
                defaults={
                    'mrp': price * decimal.Decimal('1.2'),
                    'selling_price': price,
                    'cost_price': price * decimal.Decimal('0.8'),
                    'stock_quantity': 50,
                    'tax_percentage': 18.0
                }
            )

            # 5. Download Image to Media Folder
            if v_created and item.get('image'):
            if item.get('image'):
                img_url = item.get('image')
                img_res = requests.get(img_url)
                if img_res.status_code == 200:
                    img_obj = ProductImage(variant=variant, is_primary=True)
                    img_obj.image.save(f"{asin}.jpg", ContentFile(img_res.content), save=True)
                try:
                    img_res = requests.get(img_url, timeout=10)
                    if img_res.status_code == 200:
                        # Only add image if variant has none
                        if not ProductImage.objects.filter(variant=variant).exists():
                            img_obj = ProductImage(variant=variant, is_primary=True)
                            img_obj.image.save(f"{asin}.jpg", ContentFile(img_res.content), save=True)
                except Exception:
                    self.stdout.write(self.style.WARNING(f"Failed to download image for {asin}"))
            
            self.stdout.write(self.style.SUCCESS(f"Saved: {product.name[:50]}..."))
            self.stdout.write(self.style.SUCCESS(f"Saved: {product.name[:30]}..."))