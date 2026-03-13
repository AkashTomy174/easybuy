from django.core.management.base import BaseCommand
from easybuy.core.models import User, Category, SubCategory, Address
from easybuy.seller.models import SellerProfile, Product, ProductVariant, ProductImage
from easybuy.user.models import Cart, Order, OrderItem
from django.utils.text import slugify
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def handle(self, *args, **kwargs):
        run()

def run():
    print("Starting database population...")
    
    # Create Admin
    print("\n1. Creating Admin user...")
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@easybuy.com',
            'role': 'ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Admin',
            'last_name': 'User'
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print(f"[OK] Admin created - Username: admin, Password: admin123")
    else:
        print(f"[OK] Admin already exists - Username: admin")
    
    # Create Sellers
    print("\n2. Creating Seller users...")
    sellers = []
    seller_data = [
        {'username': 'seller1', 'email': 'seller1@easybuy.com', 'first_name': 'John', 'last_name': 'Electronics', 'business': 'TechWorld Store'},
        {'username': 'seller2', 'email': 'seller2@easybuy.com', 'first_name': 'Sarah', 'last_name': 'Fashion', 'business': 'Fashion Hub'},
        {'username': 'seller3', 'email': 'seller3@easybuy.com', 'first_name': 'Mike', 'last_name': 'Books', 'business': 'BookMart'},
    ]
    
    for data in seller_data:
        seller, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'role': 'SELLER',
                'first_name': data['first_name'],
                'last_name': data['last_name']
            }
        )
        if created:
            seller.set_password('seller123')
            seller.save()
            print(f"[OK] Seller created - Username: {data['username']}, Password: seller123")
        else:
            print(f"[OK] Seller already exists - Username: {data['username']}")
        
        # Create Seller Profile
        profile, _ = SellerProfile.objects.get_or_create(
            user=seller,
            defaults={
                'store_name': data['business'],
                'store_slug': slugify(data['business']),
                'gst_number': f'GST{len(sellers)}234567890',
                'pan_number': f'PAN{len(sellers)}23456',
                'bank_account_number': f'123456789{len(sellers)}',
                'ifsc_code': 'SBIN0001234',
                'business_address': '123 Business Street, Mumbai',
                'status': 'APPROVED'
            }
        )
        sellers.append(seller)
    
    # Create Customers
    print("\n3. Creating Customer users...")
    customers = []
    customer_data = [
        {'username': 'customer1', 'email': 'customer1@gmail.com', 'first_name': 'Alice', 'last_name': 'Smith'},
        {'username': 'customer2', 'email': 'customer2@gmail.com', 'first_name': 'Bob', 'last_name': 'Johnson'},
    ]
    
    for data in customer_data:
        customer, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': data['email'],
                'role': 'CUSTOMER',
                'first_name': data['first_name'],
                'last_name': data['last_name']
            }
        )
        if created:
            customer.set_password('customer123')
            customer.save()
            print(f"[OK] Customer created - Username: {data['username']}, Password: customer123")
        else:
            print(f"[OK] Customer already exists - Username: {data['username']}")
        customers.append(customer)
    
    # Create Categories
    print("\n4. Creating Categories...")
    categories_data = {
        'Electronics': ['Smartphones', 'Laptops', 'Headphones', 'Cameras'],
        'Fashion': ['Men Clothing', 'Women Clothing', 'Shoes', 'Accessories'],
        'Books': ['Fiction', 'Non-Fiction', 'Educational', 'Comics'],
        'Home & Kitchen': ['Furniture', 'Appliances', 'Decor', 'Cookware'],
    }
    
    categories = {}
    for cat_name, subcats in categories_data.items():
        category, created = Category.objects.get_or_create(
            name=cat_name,
            defaults={'slug': slugify(cat_name)}
        )
        if created:
            print(f"[OK] Category created: {cat_name}")
        categories[cat_name] = category
        
        for subcat_name in subcats:
            SubCategory.objects.get_or_create(
                name=subcat_name,
                category=category
            )
    
    # Create Products
    print("\n5. Creating Products...")
    products_data = [
        {'name': 'iPhone 15 Pro', 'category': 'Electronics', 'subcategory': 'Smartphones', 'price': 129999, 'brand': 'Apple'},
        {'name': 'Samsung Galaxy S24', 'category': 'Electronics', 'subcategory': 'Smartphones', 'price': 89999, 'brand': 'Samsung'},
        {'name': 'MacBook Pro M3', 'category': 'Electronics', 'subcategory': 'Laptops', 'price': 199999, 'brand': 'Apple'},
        {'name': 'Dell XPS 15', 'category': 'Electronics', 'subcategory': 'Laptops', 'price': 149999, 'brand': 'Dell'},
        {'name': 'Sony WH-1000XM5', 'category': 'Electronics', 'subcategory': 'Headphones', 'price': 29999, 'brand': 'Sony'},
        {'name': 'Men Casual Shirt', 'category': 'Fashion', 'subcategory': 'Men Clothing', 'price': 1299, 'brand': 'Levi\'s'},
        {'name': 'Women Summer Dress', 'category': 'Fashion', 'subcategory': 'Women Clothing', 'price': 1999, 'brand': 'Zara'},
        {'name': 'Nike Running Shoes', 'category': 'Fashion', 'subcategory': 'Shoes', 'price': 4999, 'brand': 'Nike'},
        {'name': 'The Great Gatsby', 'category': 'Books', 'subcategory': 'Fiction', 'price': 299, 'brand': 'Penguin'},
        {'name': 'Atomic Habits', 'category': 'Books', 'subcategory': 'Non-Fiction', 'price': 499, 'brand': 'Random House'},
    ]
    
    products = []
    for idx, prod_data in enumerate(products_data):
        seller_profile = SellerProfile.objects.filter(user=sellers[idx % len(sellers)]).first()
        if not seller_profile:
            continue
        category = categories[prod_data['category']]
        subcategory = SubCategory.objects.get(name=prod_data['subcategory'], category=category)
        
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            seller=seller_profile,
            defaults={
                'slug': slugify(prod_data['name']),
                'description': f"High quality {prod_data['name']} with excellent features and performance.",
                'subcategory': subcategory,
                'brand': prod_data['brand'],
                'model_number': f'MODEL{1000 + idx}',
                'approval_status': 'APPROVED'
            }
        )
        if created:
            print(f"[OK] Product created: {prod_data['name']}")
        
        # Create Product Variant
        variant, _ = ProductVariant.objects.get_or_create(
            product=product,
            sku_code=f'SKU{1000 + idx}',
            defaults={
                'mrp': Decimal(prod_data['price']),
                'selling_price': Decimal(prod_data['price'] * 0.9),
                'cost_price': Decimal(prod_data['price'] * 0.7),
                'stock_quantity': random.randint(10, 100),
                'tax_percentage': 18.0
            }
        )
        products.append((product, variant))
    
    # Create Addresses for customers
    print("\n6. Creating Addresses...")
    for customer in customers:
        Address.objects.get_or_create(
            user=customer,
            defaults={
                'full_name': customer.get_full_name(),
                'phone_number': '9876543210',
                'house_info': '123 Main Street',
                'locality': 'Andheri West',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'country': 'India',
                'pincode': '400001',
                'address_type': 'HOME',
                'is_default': True
            }
        )
    
    # Skip order creation for now
    print("\n7. Skipping Sample Orders (can be created manually)...")
    
    print("\n" + "="*50)
    print("DATABASE POPULATED SUCCESSFULLY!")
    print("="*50)
    print("\nLOGIN CREDENTIALS:")
    print("\nADMIN:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\nSELLERS:")
    print("   Username: seller1, seller2, seller3")
    print("   Password: seller123")
    print("\nCUSTOMERS:")
    print("   Username: customer1, customer2")
    print("   Password: customer123")
    print("\n" + "="*50)
