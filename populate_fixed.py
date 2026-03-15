# populate_db.py
import os, django, random, uuid
from datetime import datetime, timedelta

# --------------------------
# Setup Django environment
# --------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.settings")
django.setup()

from django.core.files import File
from django.utils import timezone
from easybuy.core.models import User, Address, Cart, CartItem, Order, OrderItem
from easybuy.easybuy_admin.models import Category, SubCategory, Banner, Offer, Discount, Coupon
from easybuy.seller.models import SellerProfile, Product, ProductVariant, ProductImage, Review, ReviewImage

# --------------------------
# Clear existing data
# --------------------------
print("Clearing old data...")
# Delete in order to respect FK constraints
ReviewImage.objects.all().delete()
Review.objects.all().delete()
ProductImage.objects.all().delete()
ProductVariant.objects.all().delete()
Product.objects.all().delete()
SellerProfile.objects.all().delete()
CartItem.objects.all().delete()
Cart.objects.all().delete()
Address.objects.all().delete()
OrderItem.objects.all().delete()
Order.objects.all().delete()
SubCategory.objects.all().delete()
Category.objects.all().delete()
Banner.objects.all().delete()
Offer.objects.all().delete()
Discount.objects.all().delete()
Coupon.objects.all().delete()
User.objects.all().delete()
print("Old data cleared.")

# --------------------------
# Create Users
# --------------------------
print("Creating users...")
users_data = [
    {"username": "alice", "email": "alice@example.com", "password": "Test@123", "role": "CUSTOMER"},
    {"username": "bob", "email": "bob@example.com", "password": "Test@123", "role": "CUSTOMER"},
    {"username": "charlie", "email": "charlie@example.com", "password": "Test@123", "role": "SELLER"},
    {"username": "admin", "email": "admin@example.com", "password": "Admin@123", "role": "ADMIN"},
]

users = []
for u in users_data:
    user = User(username=u["username"], email=u["email"], is_active=True, role=u["role"])
    user.set_password(u["password"])
    user.save()
    users.append(user)
print("Users created.")

# --------------------------
# Create Addresses for customers
# --------------------------
print("Creating addresses...")
for user in users:
    if user.role == "CUSTOMER":
        Address.objects.create(
            user=user,
            full_name=user.username.title(),
            phone_number=f"99988877{random.randint(10,99)}",
            pincode="682001",
            locality="Test Locality",
            house_info="123, Test Street",
            city="Kochi",
            state="Kerala",
            country="India",
            landmark="Near Park",
            address_type="Home",
            is_default=True
        )
print("Addresses created.")

# --------------------------
# Create Categories & Subcategories
# --------------------------
print("Creating categories...")
categories = []
cat_names = ["Electronics", "Fashion", "Books"]
for name in cat_names:
    cat = Category.objects.create(name=name, slug=name.lower())
    categories.append(cat)

subcats = []
for cat in categories:
    for i in range(1, 3):
        sub = SubCategory.objects.create(name=f"{cat.name} Sub{i}", category=cat)
        subcats.append(sub)
print("Categories and subcategories created.")

# --------------------------
# Create Sellers
# --------------------------
print("Creating sellers...")
sellers = []
for user in users:
    if user.role == "SELLER":
        seller = SellerProfile.objects.create(
            user=user,
            store_name=f"{user.username} Store",
            store_slug=f"{user.username.lower()}-store",
            gst_number="GST123456",
            pan_number="PAN123456",
            bank_account_number="1234567890",
            ifsc_code="IFSC0001",
            doc="documents/dummy.pdf",
            business_address="Kochi, Kerala",
            status="APPROVED"
        )
        sellers.append(seller)
print("Sellers created.")

# --------------------------
# Create Products & Variants
# --------------------------
print("Creating products and variants...")
products = []
variants = []

for seller in sellers:
    for subcat in subcats:
        for i in range(1,3):
            prod_name = f"{subcat.name} Product{i}"
            prod = Product.objects.create(
                seller=seller,
                subcategory=subcat,
                name=prod_name,
                description="Test product description",
                brand="BrandX",
                model_number=f"M{i}",
                is_cancellable=True,
                is_returnable=True,
                return_days=7,
                approval_status="APPROVED",
            )
            products.append(prod)
            # Variant
            var = ProductVariant.objects.create(
                product=prod,
                sku_code=f"{prod_name[:3]}-{i}-{uuid.uuid4().hex[:4]}",
                mrp=1000+i*10,
                selling_price=900+i*10,
                cost_price=800+i*10,
                stock_quantity=50,
                tax_percentage=18
            )
            variants.append(var)
            # Images (3 per variant)
            for j in range(1,4):
                ProductImage.objects.create(
                    variant=var,
                    image=f"products/variants/{prod_name.replace(' ','_').lower()}_img_{j}.jpg",
                    alt_text=f"{prod_name} image {j}",
                    is_primary=(j==1)
                )
print("Products, variants, and images created.")

# --------------------------
# Create Reviews & ReviewImages
# --------------------------
print("Creating reviews and review images...")
for prod in products[:5]:  # create reviews for first 5 products
    for user in users:
        if user.role=="CUSTOMER":
            review = Review.objects.create(
                user=user,
                product=prod,
                rating=random.randint(3,5),
                comment=f"This is a review by {user.username} for {prod.name}"
            )
            # Add 2 images per review
            for k in range(1,3):
                ReviewImage.objects.create(
                    review=review,
                    image=f"reviews/images/{prod.name.replace(' ','_').lower()}_review_img_{k}.jpg"
                )
print("Reviews and images created.")

# --------------------------
# Create Carts & CartItems
# --------------------------
print("Creating carts...")
for user in users:
    if user.role=="CUSTOMER":
        cart = Cart.objects.create(user=user, total_amount=0)
        # Add 2 random variants
        chosen_variants = random.sample(variants, 2)
        total = 0
        for var in chosen_variants:
            qty = random.randint(1,3)
            CartItem.objects.create(cart=cart, variant=var, quantity=qty, price_at_time=var.selling_price)
            total += qty * var.selling_price
        cart.total_amount = total
        cart.save()
print("Carts created.")

print("Database population completed successfully!")