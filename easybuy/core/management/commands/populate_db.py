from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from django.core.files.base import ContentFile
from easybuy.core.models import Category, SubCategory, Address
from easybuy.seller.models import SellerProfile, Product, ProductVariant, ProductImage
from easybuy.user.models import Order, OrderItem, Review, Cart, CartItem
from decimal import Decimal
import random
from datetime import timedelta
import requests
from io import BytesIO

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with professional dummy data'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Wiping database...'))
        self.wipe_database()
        
        self.stdout.write(self.style.SUCCESS('Creating users...'))
        self.create_users()
        
        self.stdout.write(self.style.SUCCESS('Creating categories...'))
        self.create_categories()
        
        self.stdout.write(self.style.SUCCESS('Creating sellers...'))
        self.create_sellers()
        
        self.stdout.write(self.style.SUCCESS('Creating products...'))
        self.create_products()
        
        self.stdout.write(self.style.SUCCESS('Creating addresses...'))
        self.create_addresses()
        
        self.stdout.write(self.style.SUCCESS('Creating orders...'))
        self.create_orders()
        
        self.stdout.write(self.style.SUCCESS('Creating reviews...'))
        self.create_reviews()
        
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))

    def wipe_database(self):
        """Delete all data from database"""
        Review.objects.all().delete()
        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        SellerProfile.objects.all().delete()
        Address.objects.all().delete()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()

    def create_users(self):
        """Create admin, sellers, and customers"""
        # Admin
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@easybuy.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            phone_number='9876543210'
        )
        
        # Customers
        self.customers = []
        customer_data = [
            ('john_doe', 'John', 'Doe', 'john.doe@gmail.com', '9876543211'),
            ('sarah_smith', 'Sarah', 'Smith', 'sarah.smith@gmail.com', '9876543212'),
            ('mike_johnson', 'Mike', 'Johnson', 'mike.j@gmail.com', '9876543213'),
            ('emily_brown', 'Emily', 'Brown', 'emily.brown@gmail.com', '9876543214'),
            ('david_wilson', 'David', 'Wilson', 'david.w@gmail.com', '9876543215'),
        ]
        
        for username, first, last, email, phone in customer_data:
            customer = User.objects.create_user(
                username=username,
                email=email,
                password='customer123',
                first_name=first,
                last_name=last,
                role='CUSTOMER',
                phone_number=phone
            )
            self.customers.append(customer)
        
        # Sellers
        self.seller_users = []
        seller_data = [
            ('techworld_seller', 'TechWorld', 'Manager', 'contact@techworld.com', '9876543220'),
            ('fashionhub_seller', 'FashionHub', 'Owner', 'info@fashionhub.com', '9876543221'),
            ('homeessentials_seller', 'HomeEssentials', 'Admin', 'support@homeessentials.com', '9876543222'),
            ('sportszone_seller', 'SportsZone', 'Manager', 'sales@sportszone.com', '9876543223'),
        ]
        
        for username, first, last, email, phone in seller_data:
            seller_user = User.objects.create_user(
                username=username,
                email=email,
                password='seller123',
                first_name=first,
                last_name=last,
                role='SELLER',
                phone_number=phone
            )
            self.seller_users.append(seller_user)

    def create_categories(self):
        """Create categories and subcategories"""
        self.categories = {}
        
        categories_data = {
            'Electronics': {
                'icon': '📱',
                'subcategories': ['Smartphones', 'Laptops', 'Tablets', 'Headphones', 'Cameras', 'Smart Watches']
            },
            'Fashion': {
                'icon': '👔',
                'subcategories': ['Men\'s Clothing', 'Women\'s Clothing', 'Shoes', 'Accessories', 'Watches']
            },
            'Home & Kitchen': {
                'icon': '🏠',
                'subcategories': ['Furniture', 'Kitchen Appliances', 'Home Decor', 'Bedding', 'Storage']
            },
            'Sports & Fitness': {
                'icon': '⚽',
                'subcategories': ['Gym Equipment', 'Sports Wear', 'Yoga & Fitness', 'Outdoor Sports', 'Cycling']
            },
            'Books & Media': {
                'icon': '📚',
                'subcategories': ['Fiction', 'Non-Fiction', 'Educational', 'Comics', 'Magazines']
            },
            'Beauty & Personal Care': {
                'icon': '💄',
                'subcategories': ['Skincare', 'Makeup', 'Haircare', 'Fragrances', 'Personal Care']
            }
        }
        
        for cat_name, cat_data in categories_data.items():
            category = Category.objects.create(
                name=cat_name,
                slug=slugify(cat_name),
                description=f'Shop the best {cat_name.lower()} products at amazing prices',
                is_active=True
            )
            
            # Download and save category image
            image_url = self.get_category_image_url(cat_name)
            self.stdout.write(f'Downloading image for category: {cat_name}...')
            image_file = self.download_image(image_url)
            
            if image_file:
                category.image_url.save(f'{slugify(cat_name)}.jpg', image_file, save=True)
                self.stdout.write(self.style.SUCCESS(f'[OK] Category image saved for {cat_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'[SKIP] No image for category {cat_name}'))
            
            self.categories[cat_name] = {
                'category': category,
                'subcategories': []
            }
            
            for subcat_name in cat_data['subcategories']:
                subcategory = SubCategory.objects.create(
                    category=category,
                    name=subcat_name,
                    slug=slugify(subcat_name),
                    is_active=True
                )
                self.categories[cat_name]['subcategories'].append(subcategory)

    def create_sellers(self):
        """Create seller profiles"""
        self.sellers = []
        
        seller_profiles = [
            {
                'user': self.seller_users[0],
                'store_name': 'TechWorld Electronics',
                'gst_number': 'GST29ABCDE1234F1Z5',
                'pan_number': 'ABCDE1234F',
                'business_address': '123 Tech Park, Electronic City, Bangalore, Karnataka - 560100',
                'bank_account_number': '1234567890123456',
                'ifsc_code': 'HDFC0001234',
            },
            {
                'user': self.seller_users[1],
                'store_name': 'FashionHub Boutique',
                'gst_number': 'GST27FGHIJ5678K2L6',
                'pan_number': 'FGHIJ5678K',
                'business_address': '456 Fashion Street, Andheri West, Mumbai, Maharashtra - 400058',
                'bank_account_number': '6543210987654321',
                'ifsc_code': 'ICIC0005678',
            },
            {
                'user': self.seller_users[2],
                'store_name': 'HomeEssentials Store',
                'gst_number': 'GST09KLMNO9012P3Q7',
                'pan_number': 'KLMNO9012P',
                'business_address': '789 Home Plaza, Sector 18, Noida, Uttar Pradesh - 201301',
                'bank_account_number': '9876543210123456',
                'ifsc_code': 'SBIN0009012',
            },
            {
                'user': self.seller_users[3],
                'store_name': 'SportsZone Pro',
                'gst_number': 'GST33PQRST3456U4V8',
                'pan_number': 'PQRST3456U',
                'business_address': '321 Sports Complex, Banjara Hills, Hyderabad, Telangana - 500034',
                'bank_account_number': '4567890123456789',
                'ifsc_code': 'AXIS0003456',
            }
        ]
        
        for profile_data in seller_profiles:
            seller = SellerProfile.objects.create(
                user=profile_data['user'],
                store_name=profile_data['store_name'],
                store_slug=slugify(profile_data['store_name']),
                gst_number=profile_data['gst_number'],
                pan_number=profile_data['pan_number'],
                business_address=profile_data['business_address'],
                bank_account_number=profile_data['bank_account_number'],
                ifsc_code=profile_data['ifsc_code'],
                status='APPROVED'
            )
            self.sellers.append(seller)

    def download_image(self, url):
        """Download image from URL and return ContentFile"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return ContentFile(response.content)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed to download image: {e}'))
        return None
    
    def get_category_image_url(self, category_name):
        """Get relevant category image URL"""
        category_key = category_name.lower()
        
        if 'electronics' in category_key:
            return 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&h=800&fit=crop'
        elif 'fashion' in category_key:
            return 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&h=800&fit=crop'
        elif 'home' in category_key or 'kitchen' in category_key:
            return 'https://images.unsplash.com/photo-1556911220-bff31c812dba?w=800&h=800&fit=crop'
        elif 'sports' in category_key or 'fitness' in category_key:
            return 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=800&h=800&fit=crop'
        elif 'books' in category_key or 'media' in category_key:
            return 'https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=800&h=800&fit=crop'
        elif 'beauty' in category_key or 'personal care' in category_key:
            return 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&h=800&fit=crop'
        else:
            return 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&h=800&fit=crop'
    
    def get_product_image_url(self, product_name, brand, variant_index=0):
        """Get relevant product image URL - using specific product images"""
        # Map specific products to image URLs from placeholder services
        product_key = product_name.lower()
        brand_key = brand.lower()
        
        # Electronics
        if 'samsung' in brand_key and 'galaxy' in product_key:
            return f'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=800&h=800&fit=crop'
        elif 'iphone' in product_key:
            return f'https://images.unsplash.com/photo-1678652197831-2d180705cd2c?w=800&h=800&fit=crop'
        elif 'oneplus' in brand_key:
            return f'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&h=800&fit=crop'
        elif 'pixel' in product_key:
            return f'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=800&h=800&fit=crop'
        elif 'dell' in brand_key and 'xps' in product_key:
            return f'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=800&h=800&fit=crop'
        elif 'macbook' in product_key:
            return f'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&h=800&fit=crop'
        elif 'hp' in brand_key and 'pavilion' in product_key:
            return f'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=800&h=800&fit=crop'
        elif 'lenovo' in brand_key and 'thinkpad' in product_key:
            return f'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&h=800&fit=crop'
        elif 'ipad' in product_key:
            return f'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800&h=800&fit=crop'
        elif 'samsung' in brand_key and 'tab' in product_key:
            return f'https://images.unsplash.com/photo-1561154464-82e9adf32764?w=800&h=800&fit=crop'
        elif 'sony' in brand_key and 'headphone' in product_key:
            return f'https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=800&h=800&fit=crop'
        elif 'airpods' in product_key:
            return f'https://images.unsplash.com/photo-1606841837239-c5a1a4a07af7?w=800&h=800&fit=crop'
        elif 'jbl' in brand_key:
            return f'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800&h=800&fit=crop'
        elif 'canon' in brand_key:
            return f'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=800&h=800&fit=crop'
        elif 'sony' in brand_key and 'alpha' in product_key:
            return f'https://images.unsplash.com/photo-1606980707986-1b0e1545e7a8?w=800&h=800&fit=crop'
        elif 'gopro' in brand_key:
            return f'https://images.unsplash.com/photo-1519558260268-cde7e03a0152?w=800&h=800&fit=crop'
        elif 'apple watch' in product_key:
            return f'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=800&h=800&fit=crop'
        elif 'samsung' in brand_key and 'watch' in product_key:
            return f'https://images.unsplash.com/photo-1617625802912-cde586faf331?w=800&h=800&fit=crop'
        # Fashion
        elif 'levi' in brand_key and 'jean' in product_key:
            return f'https://images.unsplash.com/photo-1542272604-787c3835535d?w=800&h=800&fit=crop'
        elif 'h&m' in brand_key or 't-shirt' in product_key:
            return f'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800&h=800&fit=crop'
        elif 'zara' in brand_key and 'shirt' in product_key:
            return f'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=800&h=800&fit=crop'
        elif 'dress' in product_key:
            return f'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=800&h=800&fit=crop'
        elif 'jacket' in product_key:
            return f'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&h=800&fit=crop'
        elif 'palazzo' in product_key:
            return f'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=800&h=800&fit=crop'
        elif 'nike' in brand_key and 'sneaker' in product_key:
            return f'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&h=800&fit=crop'
        elif 'puma' in brand_key:
            return f'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=800&h=800&fit=crop'
        elif 'clarks' in brand_key:
            return f'https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=800&h=800&fit=crop'
        elif 'ray-ban' in brand_key or 'aviator' in product_key:
            return f'https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&h=800&fit=crop'
        elif 'wallet' in product_key:
            return f'https://images.unsplash.com/photo-1627123424574-724758594e93?w=800&h=800&fit=crop'
        elif 'belt' in product_key:
            return f'https://images.unsplash.com/photo-1624222247344-550fb60583bb?w=800&h=800&fit=crop'
        elif 'titan' in brand_key or ('watch' in product_key and 'analog' in product_key):
            return f'https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=800&h=800&fit=crop'
        elif 'casio' in brand_key and 'g-shock' in product_key:
            return f'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&h=800&fit=crop'
        # Home & Kitchen
        elif 'philips' in brand_key and 'fryer' in product_key:
            return f'https://images.unsplash.com/photo-1585515320310-259814833e62?w=800&h=800&fit=crop'
        elif 'dyson' in brand_key and 'vacuum' in product_key:
            return f'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=800&h=800&fit=crop'
        elif 'instant pot' in brand_key:
            return f'https://images.unsplash.com/photo-1585515320310-259814833e62?w=800&h=800&fit=crop'
        elif 'blender' in product_key:
            return f'https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=800&h=800&fit=crop'
        elif 'mixer' in product_key:
            return f'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=800&h=800&fit=crop'
        elif 'dishwasher' in product_key:
            return f'https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=800&h=800&fit=crop'
        elif 'armchair' in product_key or 'poang' in product_key:
            return f'https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=800&h=800&fit=crop'
        elif 'table' in product_key and 'study' in product_key:
            return f'https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=800&h=800&fit=crop'
        elif 'sofa' in product_key:
            return f'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&h=800&fit=crop'
        elif 'bedsheet' in product_key:
            return f'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&h=800&fit=crop'
        elif 'comforter' in product_key:
            return f'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=800&h=800&fit=crop'
        # Sports & Fitness
        elif 'adidas' in brand_key and 'ultraboost' in product_key:
            return f'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=800&h=800&fit=crop'
        elif 'fitbit' in brand_key:
            return f'https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=800&h=800&fit=crop'
        elif 'treadmill' in product_key:
            return f'https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=800&h=800&fit=crop'
        elif 'dumbbell' in product_key:
            return f'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=800&h=800&fit=crop'
        elif 'yoga mat' in product_key:
            return f'https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=800&h=800&fit=crop'
        elif 'football' in product_key:
            return f'https://images.unsplash.com/photo-1614632537423-1e6c2e7e0aab?w=800&h=800&fit=crop'
        elif 'badminton' in product_key:
            return f'https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=800&h=800&fit=crop'
        elif 'cricket' in product_key and 'bat' in product_key:
            return f'https://images.unsplash.com/photo-1531415074968-036ba1b575da?w=800&h=800&fit=crop'
        elif 'bicycle' in product_key:
            return f'https://images.unsplash.com/photo-1576435728678-68d0fbf94e91?w=800&h=800&fit=crop'
        elif 'gym bag' in product_key:
            return f'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&h=800&fit=crop'
        # Books & Media
        elif 'atomic habits' in product_key or 'book' in product_key:
            return f'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=800&h=800&fit=crop'
        # Beauty & Personal Care
        elif 'lipstick' in product_key:
            return f'https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=800&h=800&fit=crop'
        elif 'foundation' in product_key:
            return f'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=800&h=800&fit=crop'
        elif 'hydro boost' in product_key or 'moisturizer' in product_key:
            return f'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=800&h=800&fit=crop'
        elif 'cleanser' in product_key:
            return f'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=800&h=800&fit=crop'
        elif 'shampoo' in product_key:
            return f'https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=800&h=800&fit=crop'
        elif 'conditioner' in product_key:
            return f'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=800&h=800&fit=crop'
        elif 'perfume' in product_key or 'fragrance' in product_key or 'ck one' in product_key:
            return f'https://images.unsplash.com/photo-1541643600914-78b084683601?w=800&h=800&fit=crop'
        elif 'razor' in product_key:
            return f'https://images.unsplash.com/photo-1629198688000-71f23e745b6e?w=800&h=800&fit=crop'
        else:
            # Generic product image
            return f'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&h=800&fit=crop'

    def create_products(self):
        """Create products with variants and images"""
        self.products = []
        
        # Electronics Products
        electronics_products = [
            {
                'name': 'Samsung Galaxy S24 Ultra',
                'brand': 'Samsung',
                'description': 'Experience the pinnacle of smartphone innovation with the Galaxy S24 Ultra. Features a stunning 6.8" Dynamic AMOLED display, powerful Snapdragon 8 Gen 3 processor, and revolutionary 200MP camera system. Built with premium titanium frame for ultimate durability.',
                'subcategory': self.categories['Electronics']['subcategories'][0],
                'variants': [
                    {'name': '256GB Titanium Black', 'sku': 'SAM-S24U-256-BLK', 'mrp': 134999, 'price': 124999, 'stock': 25},
                    {'name': '512GB Titanium Gray', 'sku': 'SAM-S24U-512-GRY', 'mrp': 144999, 'price': 134999, 'stock': 15},
                ]
            },
            {
                'name': 'Apple iPhone 15 Pro Max',
                'brand': 'Apple',
                'description': 'The most advanced iPhone ever. Featuring aerospace-grade titanium design, A17 Pro chip with 6-core GPU, ProMotion display with Always-On, and professional camera system with 5x optical zoom. iOS 17 brings powerful new features.',
                'subcategory': self.categories['Electronics']['subcategories'][0],
                'variants': [
                    {'name': '256GB Natural Titanium', 'sku': 'APL-IP15PM-256-NAT', 'mrp': 159900, 'price': 154900, 'stock': 20},
                    {'name': '512GB Blue Titanium', 'sku': 'APL-IP15PM-512-BLU', 'mrp': 174900, 'price': 169900, 'stock': 12},
                ]
            },
            {
                'name': 'OnePlus 12 5G',
                'brand': 'OnePlus',
                'description': 'Flagship killer with Snapdragon 8 Gen 3, 120Hz AMOLED display, 100W fast charging, and Hasselblad camera system. Premium design with alert slider and OxygenOS 14.',
                'subcategory': self.categories['Electronics']['subcategories'][0],
                'variants': [
                    {'name': '256GB Flowy Emerald', 'sku': 'OP-12-256-EMR', 'mrp': 64999, 'price': 59999, 'stock': 30},
                ]
            },
            {
                'name': 'Google Pixel 8 Pro',
                'brand': 'Google',
                'description': 'Pure Android experience with Google Tensor G3 chip, exceptional AI-powered camera, 7 years of updates, and stunning 6.7" LTPO OLED display. Best-in-class computational photography.',
                'subcategory': self.categories['Electronics']['subcategories'][0],
                'variants': [
                    {'name': '256GB Obsidian', 'sku': 'GOO-P8P-256-OBS', 'mrp': 106999, 'price': 99999, 'stock': 18},
                ]
            },
            {
                'name': 'Dell XPS 15 Laptop',
                'brand': 'Dell',
                'description': 'Premium performance laptop with 15.6" 4K OLED InfinityEdge display, Intel Core i7-13700H processor, NVIDIA RTX 4060 graphics, 32GB RAM, and 1TB SSD. Perfect for creators and professionals. Sleek aluminum chassis with carbon fiber palm rest.',
                'subcategory': self.categories['Electronics']['subcategories'][1],
                'variants': [
                    {'name': 'i7/32GB/1TB/RTX4060', 'sku': 'DELL-XPS15-I7-32-1T', 'mrp': 189990, 'price': 179990, 'stock': 10},
                ]
            },
            {
                'name': 'MacBook Pro 16" M3 Max',
                'brand': 'Apple',
                'description': 'Supercharged for pros. The most powerful MacBook Pro ever with M3 Max chip, up to 128GB unified memory, stunning Liquid Retina XDR display, and up to 22 hours battery life. Perfect for video editing, 3D rendering, and software development.',
                'subcategory': self.categories['Electronics']['subcategories'][1],
                'variants': [
                    {'name': 'M3 Max/48GB/1TB/Space Black', 'sku': 'APL-MBP16-M3M-48-1T', 'mrp': 349900, 'price': 339900, 'stock': 8},
                ]
            },
            {
                'name': 'HP Pavilion Gaming Laptop',
                'brand': 'HP',
                'description': 'Affordable gaming laptop with AMD Ryzen 7, NVIDIA RTX 3050, 16GB RAM, 512GB SSD, and 15.6" 144Hz display. Perfect for gaming and content creation on a budget.',
                'subcategory': self.categories['Electronics']['subcategories'][1],
                'variants': [
                    {'name': 'Ryzen7/16GB/512GB/RTX3050', 'sku': 'HP-PAV-R7-16-512', 'mrp': 74990, 'price': 69990, 'stock': 15},
                ]
            },
            {
                'name': 'Lenovo ThinkPad X1 Carbon',
                'brand': 'Lenovo',
                'description': 'Business ultrabook with Intel Core i7, 16GB RAM, 512GB SSD, 14" 2K display, and legendary ThinkPad keyboard. Military-grade durability with carbon fiber construction.',
                'subcategory': self.categories['Electronics']['subcategories'][1],
                'variants': [
                    {'name': 'i7/16GB/512GB', 'sku': 'LEN-X1C-I7-16-512', 'mrp': 149990, 'price': 139990, 'stock': 12},
                ]
            },
            {
                'name': 'iPad Pro 12.9" M2',
                'brand': 'Apple',
                'description': 'Ultimate iPad experience with M2 chip, Liquid Retina XDR display, Apple Pencil hover, and all-day battery life. Perfect for creative professionals.',
                'subcategory': self.categories['Electronics']['subcategories'][2],
                'variants': [
                    {'name': '256GB WiFi Space Gray', 'sku': 'APL-IPADP-256-SG', 'mrp': 112900, 'price': 109900, 'stock': 20},
                ]
            },
            {
                'name': 'Samsung Galaxy Tab S9',
                'brand': 'Samsung',
                'description': 'Premium Android tablet with Snapdragon 8 Gen 2, 11" 120Hz display, S Pen included, and IP68 water resistance. Perfect for productivity and entertainment.',
                'subcategory': self.categories['Electronics']['subcategories'][2],
                'variants': [
                    {'name': '128GB Graphite', 'sku': 'SAM-TABS9-128-GRA', 'mrp': 76999, 'price': 72999, 'stock': 25},
                ]
            },
            {
                'name': 'Sony WH-1000XM5 Headphones',
                'brand': 'Sony',
                'description': 'Industry-leading noise cancellation with two processors controlling 8 microphones. Premium sound quality with 30mm drivers, LDAC support, and 360 Reality Audio. Up to 30 hours battery life with quick charging. Luxurious comfort for all-day wear.',
                'subcategory': self.categories['Electronics']['subcategories'][3],
                'variants': [
                    {'name': 'Black', 'sku': 'SONY-WH1000XM5-BLK', 'mrp': 34990, 'price': 29990, 'stock': 40},
                    {'name': 'Silver', 'sku': 'SONY-WH1000XM5-SLV', 'mrp': 34990, 'price': 29990, 'stock': 30},
                ]
            },
            {
                'name': 'Apple AirPods Pro 2nd Gen',
                'brand': 'Apple',
                'description': 'Premium wireless earbuds with active noise cancellation, adaptive transparency, spatial audio, and MagSafe charging case. Up to 6 hours listening time.',
                'subcategory': self.categories['Electronics']['subcategories'][3],
                'variants': [
                    {'name': 'White', 'sku': 'APL-APP2-WHT', 'mrp': 26900, 'price': 24900, 'stock': 35},
                ]
            },
            {
                'name': 'JBL Flip 6 Bluetooth Speaker',
                'brand': 'JBL',
                'description': 'Portable Bluetooth speaker with powerful sound, IP67 waterproof rating, 12 hours playtime, and PartyBoost feature. Perfect for outdoor adventures.',
                'subcategory': self.categories['Electronics']['subcategories'][3],
                'variants': [
                    {'name': 'Black', 'sku': 'JBL-FLIP6-BLK', 'mrp': 12999, 'price': 9999, 'stock': 50},
                ]
            },
            {
                'name': 'Canon EOS R6 Mark II',
                'brand': 'Canon',
                'description': 'Professional full-frame mirrorless camera with 24.2MP sensor, up to 40fps continuous shooting, 6K video recording, and advanced AI-powered autofocus. Perfect for wildlife, sports, and professional photography. Weather-sealed magnesium alloy body.',
                'subcategory': self.categories['Electronics']['subcategories'][4],
                'variants': [
                    {'name': 'Body Only', 'sku': 'CAN-R6M2-BODY', 'mrp': 249990, 'price': 239990, 'stock': 5},
                ]
            },
            {
                'name': 'Sony Alpha A7 IV',
                'brand': 'Sony',
                'description': 'Versatile full-frame mirrorless camera with 33MP sensor, 4K 60fps video, real-time tracking AF, and 5-axis stabilization. Perfect for hybrid shooters.',
                'subcategory': self.categories['Electronics']['subcategories'][4],
                'variants': [
                    {'name': 'Body Only', 'sku': 'SONY-A7IV-BODY', 'mrp': 229990, 'price': 219990, 'stock': 6},
                ]
            },
            {
                'name': 'GoPro Hero 12 Black',
                'brand': 'GoPro',
                'description': 'Ultimate action camera with 5.3K video, HyperSmooth 6.0 stabilization, waterproof to 10m, and HDR photo/video. Perfect for adventure enthusiasts.',
                'subcategory': self.categories['Electronics']['subcategories'][4],
                'variants': [
                    {'name': 'Black', 'sku': 'GOP-H12-BLK', 'mrp': 44990, 'price': 39990, 'stock': 20},
                ]
            },
            {
                'name': 'Apple Watch Series 9',
                'brand': 'Apple',
                'description': 'Advanced smartwatch with S9 chip, always-on Retina display, ECG, blood oxygen monitoring, and fitness tracking. Seamless integration with iPhone.',
                'subcategory': self.categories['Electronics']['subcategories'][5],
                'variants': [
                    {'name': '45mm GPS Midnight', 'sku': 'APL-AW9-45-MID', 'mrp': 45900, 'price': 42900, 'stock': 25},
                ]
            },
            {
                'name': 'Samsung Galaxy Watch 6',
                'brand': 'Samsung',
                'description': 'Premium smartwatch with Wear OS, advanced health tracking, sleep coaching, and personalized heart rate zones. Elegant design with sapphire crystal.',
                'subcategory': self.categories['Electronics']['subcategories'][5],
                'variants': [
                    {'name': '44mm Graphite', 'sku': 'SAM-GW6-44-GRA', 'mrp': 32999, 'price': 29999, 'stock': 30},
                ]
            },
        ]
        
        # Fashion Products
        fashion_products = [
            {
                'name': 'Levi\'s 511 Slim Fit Jeans',
                'brand': 'Levi\'s',
                'description': 'Classic slim fit jeans crafted from premium stretch denim. Features a modern slim leg that sits below the waist with a streamlined fit through the hip and thigh. Durable construction with signature Levi\'s stitching and leather patch.',
                'subcategory': self.categories['Fashion']['subcategories'][0],
                'variants': [
                    {'name': 'Dark Blue - 32W/34L', 'sku': 'LEVI-511-DB-3234', 'mrp': 4999, 'price': 3999, 'stock': 50},
                    {'name': 'Black - 32W/34L', 'sku': 'LEVI-511-BLK-3234', 'mrp': 4999, 'price': 3999, 'stock': 45},
                    {'name': 'Light Blue - 34W/34L', 'sku': 'LEVI-511-LB-3434', 'mrp': 4999, 'price': 3999, 'stock': 40},
                ]
            },
            {
                'name': 'H&M Cotton T-Shirt Pack',
                'brand': 'H&M',
                'description': 'Premium cotton t-shirts in pack of 3. Soft, breathable fabric with regular fit. Perfect for everyday wear. Available in classic colors.',
                'subcategory': self.categories['Fashion']['subcategories'][0],
                'variants': [
                    {'name': 'Pack of 3 - L', 'sku': 'HM-TSHIRT-3PK-L', 'mrp': 1999, 'price': 1499, 'stock': 60},
                ]
            },
            {
                'name': 'Zara Formal Shirt',
                'brand': 'Zara',
                'description': 'Elegant formal shirt with slim fit design. Made from premium cotton blend with wrinkle-resistant finish. Perfect for office and formal occasions.',
                'subcategory': self.categories['Fashion']['subcategories'][0],
                'variants': [
                    {'name': 'White - M', 'sku': 'ZARA-SHIRT-WHT-M', 'mrp': 2999, 'price': 2499, 'stock': 35},
                    {'name': 'Blue - L', 'sku': 'ZARA-SHIRT-BLU-L', 'mrp': 2999, 'price': 2499, 'stock': 30},
                ]
            },
            {
                'name': 'Mango Floral Dress',
                'brand': 'Mango',
                'description': 'Beautiful floral print dress with flowing silhouette. Made from lightweight fabric perfect for summer. Features adjustable straps and side pockets.',
                'subcategory': self.categories['Fashion']['subcategories'][1],
                'variants': [
                    {'name': 'Floral Print - M', 'sku': 'MAN-DRESS-FLR-M', 'mrp': 3999, 'price': 2999, 'stock': 25},
                ]
            },
            {
                'name': 'Forever 21 Denim Jacket',
                'brand': 'Forever 21',
                'description': 'Classic denim jacket with vintage wash. Features button closure, chest pockets, and adjustable cuffs. Perfect layering piece for any season.',
                'subcategory': self.categories['Fashion']['subcategories'][1],
                'variants': [
                    {'name': 'Light Blue - S', 'sku': 'F21-JACKET-LB-S', 'mrp': 2999, 'price': 1999, 'stock': 30},
                ]
            },
            {
                'name': 'Vero Moda Palazzo Pants',
                'brand': 'Vero Moda',
                'description': 'Comfortable palazzo pants with wide leg design. Made from soft, breathable fabric. Features elastic waistband and side pockets.',
                'subcategory': self.categories['Fashion']['subcategories'][1],
                'variants': [
                    {'name': 'Black - M', 'sku': 'VM-PALAZZO-BLK-M', 'mrp': 1999, 'price': 1499, 'stock': 40},
                ]
            },
            {
                'name': 'Nike Air Max 270 Sneakers',
                'brand': 'Nike',
                'description': 'Iconic lifestyle sneakers featuring Nike\'s largest Air unit yet for unparalleled comfort. Breathable mesh upper with synthetic overlays, foam midsole, and rubber outsole. Perfect blend of style and comfort for everyday wear.',
                'subcategory': self.categories['Fashion']['subcategories'][2],
                'variants': [
                    {'name': 'White/Black - UK 9', 'sku': 'NIKE-AM270-WB-9', 'mrp': 14995, 'price': 12995, 'stock': 30},
                    {'name': 'Triple Black - UK 10', 'sku': 'NIKE-AM270-TB-10', 'mrp': 14995, 'price': 12995, 'stock': 25},
                ]
            },
            {
                'name': 'Puma RS-X Sneakers',
                'brand': 'Puma',
                'description': 'Retro-inspired running shoes with bold design. Features cushioned midsole, durable rubber outsole, and breathable mesh upper. Perfect for casual wear.',
                'subcategory': self.categories['Fashion']['subcategories'][2],
                'variants': [
                    {'name': 'White/Blue - UK 9', 'sku': 'PUMA-RSX-WB-9', 'mrp': 8999, 'price': 6999, 'stock': 35},
                ]
            },
            {
                'name': 'Clarks Desert Boots',
                'brand': 'Clarks',
                'description': 'Classic desert boots with premium suede leather. Features crepe rubber sole and signature Clarks comfort. Perfect for smart-casual occasions.',
                'subcategory': self.categories['Fashion']['subcategories'][2],
                'variants': [
                    {'name': 'Sand Suede - UK 9', 'sku': 'CLK-DESERT-SND-9', 'mrp': 12999, 'price': 9999, 'stock': 20},
                ]
            },
            {
                'name': 'Ray-Ban Aviator Classic',
                'brand': 'Ray-Ban',
                'description': 'Timeless aviator sunglasses with gold metal frame and crystal green G-15 lenses. 100% UV protection with superior clarity and comfort. Includes premium case and cleaning cloth. The original pilot sunglasses since 1937.',
                'subcategory': self.categories['Fashion']['subcategories'][3],
                'variants': [
                    {'name': 'Gold/Green - 58mm', 'sku': 'RB-AV-GG-58', 'mrp': 12990, 'price': 10990, 'stock': 35},
                ]
            },
            {
                'name': 'Michael Kors Leather Wallet',
                'brand': 'Michael Kors',
                'description': 'Luxury leather wallet with multiple card slots, bill compartments, and coin pocket. Features signature MK logo and premium craftsmanship.',
                'subcategory': self.categories['Fashion']['subcategories'][3],
                'variants': [
                    {'name': 'Brown Leather', 'sku': 'MK-WALLET-BRN', 'mrp': 8999, 'price': 6999, 'stock': 25},
                ]
            },
            {
                'name': 'Fossil Leather Belt',
                'brand': 'Fossil',
                'description': 'Classic leather belt with reversible design. Features polished buckle and genuine leather construction. Perfect for formal and casual wear.',
                'subcategory': self.categories['Fashion']['subcategories'][3],
                'variants': [
                    {'name': 'Black/Brown - 34', 'sku': 'FOS-BELT-BB-34', 'mrp': 3999, 'price': 2999, 'stock': 40},
                ]
            },
            {
                'name': 'Titan Edge Analog Watch',
                'brand': 'Titan',
                'description': 'Ultra-slim analog watch with stainless steel case and leather strap. Features scratch-resistant sapphire crystal and water resistance up to 30m.',
                'subcategory': self.categories['Fashion']['subcategories'][4],
                'variants': [
                    {'name': 'Silver/Black', 'sku': 'TIT-EDGE-SB', 'mrp': 9995, 'price': 7995, 'stock': 30},
                ]
            },
            {
                'name': 'Casio G-Shock Digital Watch',
                'brand': 'Casio',
                'description': 'Rugged digital watch with shock resistance, 200m water resistance, world time, stopwatch, and LED backlight. Built to last.',
                'subcategory': self.categories['Fashion']['subcategories'][4],
                'variants': [
                    {'name': 'Black', 'sku': 'CAS-GSHOCK-BLK', 'mrp': 11995, 'price': 9995, 'stock': 35},
                ]
            },
        ]
        
        # Home & Kitchen Products
        home_products = [
            {
                'name': 'Philips Air Fryer XXL',
                'brand': 'Philips',
                'description': 'Extra-large air fryer with Rapid Air technology for healthier cooking with up to 90% less fat. 7.3L capacity perfect for families, digital touchscreen, 7 preset programs, and dishwasher-safe parts. Cook, bake, grill, and roast with ease.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': 'Black XXL 7.3L', 'sku': 'PHI-AF-XXL-BLK', 'mrp': 24995, 'price': 19995, 'stock': 20},
                ]
            },
            {
                'name': 'Dyson V15 Detect Vacuum',
                'brand': 'Dyson',
                'description': 'Intelligent cordless vacuum with laser detection technology that reveals invisible dust. Powerful suction with up to 60 minutes runtime, LCD screen showing real-time particle count, and advanced filtration system. Complete with 8 accessories.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': 'Absolute', 'sku': 'DYS-V15-ABS', 'mrp': 64900, 'price': 59900, 'stock': 12},
                ]
            },
            {
                'name': 'Instant Pot Duo Plus',
                'brand': 'Instant Pot',
                'description': '9-in-1 electric pressure cooker with 15 smart programs. Features pressure cook, slow cook, rice cooker, steamer, sauté, yogurt maker, and warmer. 6L capacity perfect for families.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': '6L Stainless Steel', 'sku': 'IP-DUO-6L-SS', 'mrp': 12995, 'price': 9995, 'stock': 25},
                ]
            },
            {
                'name': 'Ninja Professional Blender',
                'brand': 'Ninja',
                'description': 'Powerful 1000W blender with Total Crushing technology. Crushes ice, blends smoothies, and purees ingredients. Includes 72oz pitcher and 2 cups.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': '1000W Black', 'sku': 'NIN-BLEND-1000-BLK', 'mrp': 8999, 'price': 6999, 'stock': 30},
                ]
            },
            {
                'name': 'KitchenAid Stand Mixer',
                'brand': 'KitchenAid',
                'description': 'Professional stand mixer with 10-speed control and 4.8L stainless steel bowl. Includes dough hook, flat beater, and wire whip. Perfect for baking enthusiasts.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': 'Empire Red', 'sku': 'KA-MIXER-RED', 'mrp': 44995, 'price': 39995, 'stock': 10},
                ]
            },
            {
                'name': 'Bosch Dishwasher',
                'brand': 'Bosch',
                'description': 'Energy-efficient dishwasher with 12 place settings, 6 wash programs, and quiet operation. Features stainless steel interior and adjustable racks.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][1],
                'variants': [
                    {'name': '12 Place Settings', 'sku': 'BOS-DW-12PS', 'mrp': 39990, 'price': 34990, 'stock': 8},
                ]
            },
            {
                'name': 'IKEA POÄNG Armchair',
                'brand': 'IKEA',
                'description': 'Comfortable armchair with layer-glued bent birch frame. Features removable cushion cover and ergonomic design. Perfect for living room or reading nook.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][0],
                'variants': [
                    {'name': 'Birch/Beige', 'sku': 'IKEA-POANG-BG', 'mrp': 12999, 'price': 9999, 'stock': 15},
                ]
            },
            {
                'name': 'Urban Ladder Study Table',
                'brand': 'Urban Ladder',
                'description': 'Modern study table with spacious work surface and storage drawer. Made from engineered wood with laminate finish. Perfect for home office.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][0],
                'variants': [
                    {'name': 'Walnut Finish', 'sku': 'UL-TABLE-WAL', 'mrp': 14999, 'price': 11999, 'stock': 12},
                ]
            },
            {
                'name': 'Pepperfry Sofa Set',
                'brand': 'Pepperfry',
                'description': '3-seater sofa with premium fabric upholstery. Features solid wood frame, high-density foam cushions, and contemporary design. Includes 5 cushions.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][0],
                'variants': [
                    {'name': 'Grey Fabric', 'sku': 'PEP-SOFA-GRY', 'mrp': 34999, 'price': 27999, 'stock': 8},
                ]
            },
            {
                'name': 'Bombay Dyeing Bedsheet Set',
                'brand': 'Bombay Dyeing',
                'description': 'Premium cotton bedsheet set with 2 pillow covers. Features vibrant prints, soft texture, and durable construction. Double bed size.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][3],
                'variants': [
                    {'name': 'Floral Print', 'sku': 'BD-SHEET-FLR', 'mrp': 2999, 'price': 1999, 'stock': 40},
                ]
            },
            {
                'name': 'Spaces Comforter Set',
                'brand': 'Spaces',
                'description': 'Reversible comforter with microfiber filling. Includes 2 pillow covers. Soft, warm, and machine washable. Perfect for all seasons.',
                'subcategory': self.categories['Home & Kitchen']['subcategories'][3],
                'variants': [
                    {'name': 'Blue/Grey', 'sku': 'SPC-COMF-BG', 'mrp': 4999, 'price': 3499, 'stock': 30},
                ]
            },
        ]
        
        # Sports Products
        sports_products = [
            {
                'name': 'Adidas Ultraboost 23 Running Shoes',
                'brand': 'Adidas',
                'description': 'Premium running shoes with responsive Boost cushioning, Primeknit+ upper for adaptive fit, and Continental rubber outsole for superior grip. Engineered for long-distance comfort and energy return. Perfect for serious runners.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][1],
                'variants': [
                    {'name': 'Core Black - UK 9', 'sku': 'ADI-UB23-BLK-9', 'mrp': 17999, 'price': 15999, 'stock': 25},
                    {'name': 'Cloud White - UK 10', 'sku': 'ADI-UB23-WHT-10', 'mrp': 17999, 'price': 15999, 'stock': 20},
                ]
            },
            {
                'name': 'Fitbit Charge 6 Fitness Tracker',
                'brand': 'Fitbit',
                'description': 'Advanced fitness tracker with built-in GPS, heart rate monitoring, sleep tracking, and 40+ exercise modes. 7-day battery life, water-resistant up to 50m, and Google integration. Track your health metrics with precision.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][2],
                'variants': [
                    {'name': 'Black/Graphite', 'sku': 'FIT-C6-BLK', 'mrp': 14999, 'price': 12999, 'stock': 40},
                ]
            },
            {
                'name': 'Reebok Treadmill',
                'brand': 'Reebok',
                'description': 'Home treadmill with 2HP motor, 12 preset programs, and LCD display. Features cushioned deck, foldable design, and max speed of 14 km/h. Perfect for home workouts.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][0],
                'variants': [
                    {'name': 'GT40S', 'sku': 'RBK-TREAD-GT40', 'mrp': 44990, 'price': 39990, 'stock': 8},
                ]
            },
            {
                'name': 'Decathlon Dumbbells Set',
                'brand': 'Decathlon',
                'description': 'Adjustable dumbbell set with weight plates. Includes 2 dumbbell bars and 8 weight plates (2kg each). Perfect for home gym and strength training.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][0],
                'variants': [
                    {'name': '20kg Set', 'sku': 'DEC-DUMB-20KG', 'mrp': 3999, 'price': 2999, 'stock': 35},
                ]
            },
            {
                'name': 'Lifelong Yoga Mat',
                'brand': 'Lifelong',
                'description': 'Premium yoga mat with anti-slip texture and extra cushioning. Made from eco-friendly TPE material. Includes carrying strap. Perfect for yoga and fitness.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][2],
                'variants': [
                    {'name': 'Purple 6mm', 'sku': 'LL-YOGA-PUR-6', 'mrp': 1499, 'price': 999, 'stock': 50},
                ]
            },
            {
                'name': 'Nivia Football',
                'brand': 'Nivia',
                'description': 'Professional football with hand-stitched construction. Features durable synthetic leather and butyl bladder. Size 5, perfect for matches and training.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][3],
                'variants': [
                    {'name': 'Size 5 White/Black', 'sku': 'NIV-FB-5-WB', 'mrp': 1299, 'price': 899, 'stock': 45},
                ]
            },
            {
                'name': 'Yonex Badminton Racket',
                'brand': 'Yonex',
                'description': 'Professional badminton racket with graphite frame. Features isometric head shape and lightweight design. Includes full cover. Perfect for intermediate to advanced players.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][3],
                'variants': [
                    {'name': 'Nanoray 20', 'sku': 'YON-BAD-NR20', 'mrp': 4999, 'price': 3999, 'stock': 20},
                ]
            },
            {
                'name': 'Cosco Cricket Bat',
                'brand': 'Cosco',
                'description': 'Kashmir willow cricket bat with full size. Features traditional shape, comfortable grip, and durable construction. Perfect for leather ball cricket.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][3],
                'variants': [
                    {'name': 'Full Size', 'sku': 'COS-BAT-FULL', 'mrp': 2999, 'price': 1999, 'stock': 25},
                ]
            },
            {
                'name': 'Hero Sprint Bicycle',
                'brand': 'Hero',
                'description': '26-inch mountain bike with 18-speed gears, front suspension, and disc brakes. Features durable steel frame and comfortable saddle. Perfect for city and trail riding.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][4],
                'variants': [
                    {'name': '26" Black/Red', 'sku': 'HERO-BIKE-26-BR', 'mrp': 14999, 'price': 12999, 'stock': 10},
                ]
            },
            {
                'name': 'Strauss Gym Bag',
                'brand': 'Strauss',
                'description': 'Spacious gym bag with multiple compartments. Features water-resistant fabric, shoe compartment, and adjustable shoulder strap. Perfect for gym and sports.',
                'subcategory': self.categories['Sports & Fitness']['subcategories'][1],
                'variants': [
                    {'name': 'Black 40L', 'sku': 'STR-BAG-BLK-40', 'mrp': 1999, 'price': 1299, 'stock': 40},
                ]
            },
        ]
        
        # Books & Media Products
        books_products = [
            {
                'name': 'Atomic Habits by James Clear',
                'brand': 'Penguin Random House',
                'description': 'Bestselling self-help book on building good habits and breaking bad ones. Practical strategies backed by science. Hardcover edition with 320 pages.',
                'subcategory': self.categories['Books & Media']['subcategories'][1],
                'variants': [
                    {'name': 'Hardcover', 'sku': 'BOOK-AH-HC', 'mrp': 799, 'price': 599, 'stock': 50},
                ]
            },
            {
                'name': 'The Psychology of Money',
                'brand': 'Harriman House',
                'description': 'Timeless lessons on wealth, greed, and happiness by Morgan Housel. Essential reading for understanding personal finance. Paperback edition.',
                'subcategory': self.categories['Books & Media']['subcategories'][1],
                'variants': [
                    {'name': 'Paperback', 'sku': 'BOOK-POM-PB', 'mrp': 450, 'price': 350, 'stock': 60},
                ]
            },
            {
                'name': 'Harry Potter Complete Collection',
                'brand': 'Bloomsbury',
                'description': 'Complete set of all 7 Harry Potter books in paperback. Includes bonus content and beautiful cover designs. Perfect gift for fans.',
                'subcategory': self.categories['Books & Media']['subcategories'][0],
                'variants': [
                    {'name': 'Box Set', 'sku': 'BOOK-HP-BOX', 'mrp': 4999, 'price': 3999, 'stock': 20},
                ]
            },
            {
                'name': 'NCERT Class 12 Physics',
                'brand': 'NCERT',
                'description': 'Official NCERT textbook for Class 12 Physics. Latest edition with updated syllabus. Essential for board exam preparation.',
                'subcategory': self.categories['Books & Media']['subcategories'][2],
                'variants': [
                    {'name': 'Latest Edition', 'sku': 'BOOK-NCERT-PHY12', 'mrp': 250, 'price': 200, 'stock': 100},
                ]
            },
            {
                'name': 'Marvel Comics Collection',
                'brand': 'Marvel',
                'description': 'Collection of 10 classic Marvel comics featuring Spider-Man, Iron Man, and Avengers. High-quality print with vibrant colors.',
                'subcategory': self.categories['Books & Media']['subcategories'][3],
                'variants': [
                    {'name': '10 Comics Set', 'sku': 'BOOK-MARVEL-10', 'mrp': 1999, 'price': 1499, 'stock': 30},
                ]
            },
        ]
        
        # Beauty & Personal Care Products
        beauty_products = [
            {
                'name': 'Lakmé Absolute Lipstick',
                'brand': 'Lakmé',
                'description': 'Long-lasting matte lipstick with rich color payoff. Enriched with vitamin E for soft, smooth lips. Available in trendy shades.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][1],
                'variants': [
                    {'name': 'Red Rush', 'sku': 'LAK-LIP-RED', 'mrp': 650, 'price': 499, 'stock': 80},
                ]
            },
            {
                'name': 'Maybelline Fit Me Foundation',
                'brand': 'Maybelline',
                'description': 'Lightweight liquid foundation with natural finish. Available in multiple shades to match Indian skin tones. Oil-free and non-comedogenic.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][1],
                'variants': [
                    {'name': 'Natural Beige', 'sku': 'MAY-FOUND-BG', 'mrp': 599, 'price': 449, 'stock': 70},
                ]
            },
            {
                'name': 'Neutrogena Hydro Boost',
                'brand': 'Neutrogena',
                'description': 'Hydrating gel cream with hyaluronic acid. Provides 48-hour hydration for soft, supple skin. Non-greasy formula suitable for all skin types.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][0],
                'variants': [
                    {'name': '50g', 'sku': 'NEU-HB-50G', 'mrp': 799, 'price': 649, 'stock': 60},
                ]
            },
            {
                'name': 'Cetaphil Gentle Cleanser',
                'brand': 'Cetaphil',
                'description': 'Gentle face cleanser for sensitive skin. Soap-free, fragrance-free formula that cleanses without stripping natural oils. Dermatologist recommended.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][0],
                'variants': [
                    {'name': '250ml', 'sku': 'CET-CLEAN-250', 'mrp': 899, 'price': 749, 'stock': 55},
                ]
            },
            {
                'name': 'L\'Oreal Paris Shampoo',
                'brand': 'L\'Oreal',
                'description': 'Total Repair 5 shampoo for damaged hair. Repairs and strengthens hair with ceramide and protein. Suitable for all hair types.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][2],
                'variants': [
                    {'name': '650ml', 'sku': 'LOR-SHAM-650', 'mrp': 599, 'price': 449, 'stock': 65},
                ]
            },
            {
                'name': 'TRESemmé Hair Conditioner',
                'brand': 'TRESemmé',
                'description': 'Keratin Smooth conditioner for frizzy hair. Provides salon-quality smoothness and shine. Leaves hair manageable and silky.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][2],
                'variants': [
                    {'name': '580ml', 'sku': 'TRE-COND-580', 'mrp': 549, 'price': 399, 'stock': 60},
                ]
            },
            {
                'name': 'Calvin Klein CK One',
                'brand': 'Calvin Klein',
                'description': 'Iconic unisex fragrance with fresh, clean scent. Features notes of bergamot, jasmine, and musk. Long-lasting EDT spray.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][3],
                'variants': [
                    {'name': '100ml EDT', 'sku': 'CK-ONE-100', 'mrp': 4999, 'price': 3999, 'stock': 25},
                ]
            },
            {
                'name': 'Gillette Fusion Razor',
                'brand': 'Gillette',
                'description': 'Premium razor with 5-blade technology for close, comfortable shave. Features precision trimmer and lubrication strip. Includes 2 cartridges.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][4],
                'variants': [
                    {'name': 'Razor + 2 Cartridges', 'sku': 'GIL-FUS-RAZ', 'mrp': 799, 'price': 599, 'stock': 50},
                ]
            },
            {
                'name': 'Nivea Soft Moisturizer',
                'brand': 'Nivea',
                'description': 'Light moisturizing cream with vitamin E and jojoba oil. Fast-absorbing formula suitable for face, body, and hands. Non-greasy finish.',
                'subcategory': self.categories['Beauty & Personal Care']['subcategories'][4],
                'variants': [
                    {'name': '200ml', 'sku': 'NIV-SOFT-200', 'mrp': 299, 'price': 249, 'stock': 75},
                ]
            },
        ]
        
        all_products = electronics_products + fashion_products + home_products + sports_products + books_products + beauty_products
        
        for idx, prod_data in enumerate(all_products):
            seller = self.sellers[idx % len(self.sellers)]
            
            product = Product.objects.create(
                seller=seller,
                subcategory=prod_data['subcategory'],
                name=prod_data['name'],
                slug=slugify(prod_data['name']),
                description=prod_data['description'],
                brand=prod_data['brand'],
                model_number=f'MODEL-{random.randint(1000, 9999)}',
                is_cancellable=True,
                is_returnable=True,
                return_days=7,
                approval_status='APPROVED',
                is_active=True
            )
            
            for var_data in prod_data['variants']:
                variant = ProductVariant.objects.create(
                    product=product,
                    sku_code=var_data['sku'],
                    mrp=Decimal(str(var_data['mrp'])),
                    selling_price=Decimal(str(var_data['price'])),
                    cost_price=Decimal(str(var_data['price'] * 0.7)),
                    stock_quantity=var_data['stock'],
                    weight=random.uniform(0.5, 5.0),
                    length=random.uniform(10, 50),
                    width=random.uniform(10, 50),
                    height=random.uniform(5, 30),
                    tax_percentage=18.0
                )
                
                # Create image with relevant product image from Unsplash
                image_url = self.get_product_image_url(product.name, product.brand)
                self.stdout.write(f'Downloading image for {variant.sku_code}...')
                image_file = self.download_image(image_url)
                
                if image_file:
                    product_image = ProductImage.objects.create(
                        variant=variant,
                        is_primary=True,
                        alt_text=f'{product.name} - {var_data["name"]}'
                    )
                    product_image.image.save(f'{variant.sku_code}.jpg', image_file, save=True)
                    self.stdout.write(self.style.SUCCESS(f'[OK] Image saved for {variant.sku_code}'))
                else:
                    # Fallback: create without image
                    ProductImage.objects.create(
                        variant=variant,
                        is_primary=True,
                        alt_text=f'{product.name} - {var_data["name"]}'
                    )
                    self.stdout.write(self.style.WARNING(f'[SKIP] No image for {variant.sku_code}'))
            
            self.products.append(product)

    def create_addresses(self):
        """Create addresses for customers"""
        addresses_data = [
            {
                'full_name': 'John Doe',
                'phone_number': '9876543211',
                'pincode': '560001',
                'locality': 'MG Road',
                'house_info': 'Flat 301, Prestige Towers',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'address_type': 'HOME',
            },
            {
                'full_name': 'Sarah Smith',
                'phone_number': '9876543212',
                'pincode': '400001',
                'locality': 'Colaba',
                'house_info': 'Apartment 5B, Sea View Residency',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'address_type': 'HOME',
            },
            {
                'full_name': 'Mike Johnson',
                'phone_number': '9876543213',
                'pincode': '110001',
                'locality': 'Connaught Place',
                'house_info': 'House No. 42, Sector 15',
                'city': 'New Delhi',
                'state': 'Delhi',
                'address_type': 'WORK',
            },
        ]
        
        for idx, addr_data in enumerate(addresses_data):
            if idx < len(self.customers):
                Address.objects.create(
                    user=self.customers[idx],
                    full_name=addr_data['full_name'],
                    phone_number=addr_data['phone_number'],
                    pincode=addr_data['pincode'],
                    locality=addr_data['locality'],
                    house_info=addr_data['house_info'],
                    city=addr_data['city'],
                    state=addr_data['state'],
                    country='India',
                    address_type=addr_data['address_type'],
                    is_default=True
                )

    def create_orders(self):
        """Create orders with different statuses"""
        self.orders = []
        
        statuses = ['CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']
        
        for i in range(15):
            customer = random.choice(self.customers)
            address = Address.objects.filter(user=customer).first()
            
            if not address:
                continue
            
            order_date = timezone.now() - timedelta(days=random.randint(1, 30))
            status = random.choice(statuses)
            
            # Select 1-3 random products
            num_items = random.randint(1, 3)
            selected_products = random.sample(self.products, min(num_items, len(self.products)))
            
            total_amount = Decimal('0')
            order_items_data = []
            
            for product in selected_products:
                variant = product.variants.first()
                if variant:
                    quantity = random.randint(1, 2)
                    price = variant.selling_price
                    total_amount += price * quantity
                    order_items_data.append({
                        'variant': variant,
                        'seller': product.seller,
                        'quantity': quantity,
                        'price': price
                    })
            
            if not order_items_data:
                continue
            
            # Add shipping and tax
            shipping = Decimal('99') if total_amount < 999 else Decimal('0')
            tax = total_amount * Decimal('0.18')
            grand_total = total_amount + shipping + tax
            
            order = Order.objects.create(
                user=customer,
                order_number=f'EB{order_date.strftime("%Y%m%d")}{random.randint(10000, 99999)}',
                total_amount=grand_total,
                payment_status='PAID' if status != 'CANCELLED' else 'PENDING',
                order_status=status,
                shipping_name=address.full_name,
                shipping_phone=address.phone_number,
                shipping_address=f'{address.house_info}, {address.locality}, {address.city}, {address.state} - {address.pincode}',
                ordered_at=order_date
            )
            
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    variant=item_data['variant'],
                    seller=item_data['seller'],
                    quantity=item_data['quantity'],
                    price_at_purchase=item_data['price'],
                    status=status
                )
            
            self.orders.append(order)

    def create_reviews(self):
        """Create reviews for delivered products"""
        delivered_orders = Order.objects.filter(order_status='DELIVERED')
        
        review_templates = [
            {
                'rating': 5,
                'comments': [
                    'Excellent product! Exceeded my expectations. Highly recommended.',
                    'Outstanding quality and fast delivery. Very satisfied with my purchase.',
                    'Perfect! Exactly what I was looking for. Great value for money.',
                    'Amazing product! Works flawlessly. Will definitely buy again.',
                    'Top-notch quality! The seller was very professional and helpful.',
                ]
            },
            {
                'rating': 4,
                'comments': [
                    'Good product overall. Minor issues but nothing major.',
                    'Pretty satisfied with the purchase. Good quality for the price.',
                    'Nice product. Delivery was quick. Would recommend.',
                    'Good value for money. Works as described.',
                    'Solid product. Met my expectations.',
                ]
            },
            {
                'rating': 3,
                'comments': [
                    'Average product. Could be better for the price.',
                    'It\'s okay. Nothing special but does the job.',
                    'Decent product but had some minor issues.',
                ]
            },
        ]
        
        for order in delivered_orders:
            # 70% chance of review
            if random.random() < 0.7:
                for item in order.items.all():
                    review_data = random.choice(review_templates)
                    comment = random.choice(review_data['comments'])
                    
                    review = Review.objects.create(
                        user=order.user,
                        product=item.variant.product,
                        rating=review_data['rating'],
                        comment=comment,
                        created_at=order.ordered_at + timedelta(days=random.randint(1, 7))
                    )
                    
                    # 50% chance seller replies
                    if random.random() < 0.5:
                        seller_replies = [
                            'Thank you for your wonderful feedback! We\'re glad you loved the product.',
                            'We appreciate your review! Thank you for choosing our store.',
                            'Thanks for your support! We\'re happy you had a great experience.',
                            'Thank you for the positive review! We look forward to serving you again.',
                        ]
                        review.seller_reply = random.choice(seller_replies)
                        review.replied_at = review.created_at + timedelta(hours=random.randint(1, 48))
                        review.save()
