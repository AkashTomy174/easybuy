# populate_db.py
import os
import django
import random
import uuid
from decimal import Decimal
from pathlib import Path
from faker import Faker
from django.utils import timezone
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Correct DJANGO_SETTINGS_MODULE for your project
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "easybuy.easybuy.settings")

# Initialize Django
django.setup()

## Core models
from easybuy.core.models import User, Address, Category, SubCategory, Banner

# User-related models
from easybuy.user.models import (
    Cart, CartItem, Wishlist, WishlistItem,
    Order, OrderItem, Review, ReviewImage, ReviewVideo
)

# Seller-related models
from easybuy.seller.models import SellerProfile, Product, ProductVariant, ProductImage

# Admin/Offer models
from easybuy.easybuy_admin.models import Offer, Discount, Coupon

fake = Faker()

# Directories for media files
BASE_MEDIA_DIR = Path("media")
PRODUCT_IMAGE_DIR = BASE_MEDIA_DIR / "products" / "variants"
REVIEW_IMAGE_DIR = BASE_MEDIA_DIR / "reviews" / "images"
REVIEW_VIDEO_DIR = BASE_MEDIA_DIR / "reviews" / "videos"
REVIEW_THUMB_DIR = BASE_MEDIA_DIR / "reviews" / "thumbnails"

# Create directories if they don't exist
for path in [PRODUCT_IMAGE_DIR, REVIEW_IMAGE_DIR, REVIEW_VIDEO_DIR, REVIEW_THUMB_DIR]:
    path.mkdir(parents=True, exist_ok=True)


def clear_data():
    print("Clearing existing data...")
    ReviewVideo.objects.all().delete()
    ReviewImage.objects.all().delete()
    Review.objects.all().delete()
    CartItem.objects.all().delete()
    Cart.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    ProductImage.objects.all().delete()
    ProductVariant.objects.all().delete()
    Product.objects.all().delete()
    SellerProfile.objects.all().delete()
    SubCategory.objects.all().delete()
    Category.objects.all().delete()
    Address.objects.all().delete()
    User.objects.all().delete()
    print("Data cleared.")


def create_users():
    print("Creating users...")
    users = []
    # Admin
    admin = User.objects.create_user(
        username="admin_user", email="admin@example.com", password="password123", role="ADMIN"
    )
    users.append(admin)
    # Sellers
    sellers = []
    for i in range(5):
        user = User.objects.create_user(
            username=f"seller{i+1}",
            email=f"seller{i+1}@example.com",
            password="password123",
            role="SELLER",
        )
        seller_profile = SellerProfile.objects.create(
            user=user,
            store_name=f"{fake.company()} Store",
            store_slug=f"store-{i+1}",
            gst_number=fake.ein(),
            pan_number=fake.bothify("?????#?????"),
            bank_account_number=fake.bban(),
            doc="",  # leave empty for testing
            ifsc_code=fake.bothify("IFSC?????"),
            business_address=fake.address(),
            status="APPROVED",
            rating=random.uniform(3.0, 5.0),
        )
        sellers.append(user)
        users.append(user)
    # Customers
    customers = []
    for i in range(10):
        user = User.objects.create_user(
            username=f"customer{i+1}",
            email=f"customer{i+1}@example.com",
            password="password123",
            role="CUSTOMER",
        )
        # Address
        Address.objects.create(
            user=user,
            full_name=fake.name(),
            phone_number=fake.phone_number(),
            pincode=fake.postcode(),
            locality=fake.city(),
            house_info=fake.building_number(),
            city=fake.city(),
            state=fake.state(),
            country=fake.country(),
            address_type="Home",
            is_default=True,
        )
        # Cart
        Cart.objects.create(user=user)
        customers.append(user)
        users.append(user)
    print("Users created.")
    return users, sellers, customers


def create_categories():
    print("Creating categories and subcategories...")
    categories = []
    subcategories = []
    for i in range(5):
        cat = Category.objects.create(
            name=fake.word().capitalize(),
            slug=f"category-{i+1}",
            description=fake.sentence(),
        )
        categories.append(cat)
        for j in range(3):
            sub = SubCategory.objects.create(
                category=cat,
                name=f"{cat.name} Sub {j+1}",
            )
            subcategories.append(sub)
    print("Categories created.")
    return categories, subcategories


def create_products(sellers, subcategories):
    print("Creating products, variants, and images...")
    products = []
    variants = []
    for seller in sellers:
        for i in range(10):  # 10 products per seller
            subcat = random.choice(subcategories)
            prod = Product.objects.create(
                seller=seller.seller_profile,
                subcategory=subcat,
                name=fake.word().capitalize() + " " + fake.word().capitalize(),
                description=fake.text(),
                brand=fake.company(),
                model_number=fake.bothify("??-####"),
                approval_status=random.choice(["APPROVED", "PENDING"]>,
            )
            products.append(prod)
            for v in range(2):  # 2 variants per product
                variant = ProductVariant.objects.create(
                    product=prod,
                    sku_code=f"SKU-{prod.id}-{v+1}",
                    mrp=Decimal(random.randint(500, 5000)),
                    selling_price=Decimal(random.randint(400, 4500)),
                    cost_price=Decimal(random.randint(300, 4000)),
                    stock_quantity=random.randint(10, 100),
                    tax_percentage=18.0,
                )
                variants.append(variant)
                # Create 3 images per variant
                for img_num in range(1, 4):
                    # Use existing generic image randomly\n                    generic_name = random.choice(['iphone.jpg', 'laptop.jpg', 'shoes.jpg', 'tshirt.jpg', 'bag.jpg', 'headphones.jpg'])\n                    ProductImage.objects.create(\n                        variant=variant,\n                        image=f"products/variants/{generic_name}",\n                        alt_text=f"{prod.name} image {img_num}",\n                        is_primary=(img_num == 1),\n                    )
    print("Products, variants, and images created.")
    return products, variants


def create_reviews(products, customers):
    print("Creating reviews with images and videos...")
    for prod in products:
        for i in range(4):  # 4 reviews per product
            user = random.choice(customers)
            review = Review.objects.create(
                user=user,
                product=prod,
                rating=random.randint(3, 5),
                comment=fake.sentence(),
            )
            # 2 images per review
            for img_num in range(1, 3):
                img_path = REVIEW_IMAGE_DIR / f"review_{review.id}_img_{img_num}.jpg"
                img_path.touch()
                ReviewImage.objects.create(
                    review=review,
                    image=str(img_path),
                )
            # 1 video + thumbnail per review
            vid_path = REVIEW_VIDEO_DIR / f"review_{review.id}_video_1.mp4"
            thumb_path = REVIEW_THUMB_DIR / f"review_{review.id}_thumb_1.jpg"
            vid_path.touch()
            thumb_path.touch()
            ReviewVideo.objects.create(
                review=review,
                video=str(vid_path),
                thumbnail=str(thumb_path),
            )
    print("Reviews, images, and videos created.")


def create_carts(customers, variants):
    print("Adding items to carts...")
    for customer in customers:
        cart = Cart.objects.get(user=customer)
        for _ in range(3):  # 3 items per cart
            variant = random.choice(variants)
            CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=random.randint(1, 3),
                price_at_time=variant.selling_price,
            )
        # Update cart total
        total = sum(item.quantity * item.price_at_time for item in cart.items.all())
        cart.total_amount = total
        cart.save()
    print("Cart items added.")


def create_orders(customers):
    print("Creating orders from carts...")
    for customer in customers:
        cart = Cart.objects.get(user=customer)
        if not cart.items.exists():
            continue
        # Use the first address of the user
        address = customer.addresses.first()
        if not address:
            continue
        order_number = f"EB{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6]}"
        subtotal = cart.total_amount
        shipping = Decimal("99") if subtotal < 999 else Decimal("0")
        tax = subtotal * Decimal("0.18")
        total = subtotal + shipping + tax

        order = Order.objects.create(
            user=customer,
            order_number=order_number,
            total_amount=total,
            payment_status="INITIATED",
            order_status="PENDING",
            shipping_name=address.full_name,
            shipping_phone=address.phone_number,
            shipping_address=f"{address.house_info}, {address.city}, {address.state}",
        )

        # Create order items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                seller=item.variant.product.seller,
                variant=item.variant,
                quantity=item.quantity,
                price_at_purchase=item.price_at_time,
            )

        # Optionally, clear the cart
        cart.items.all().delete()
        cart.total_amount = 0
        cart.save()
    print("Orders created.")


def main():
    clear_data()
    users, sellers, customers = create_users()
    categories, subcategories = create_categories()
    products, variants = create_products(sellers, subcategories)
    create_reviews(products, customers)
    create_carts(customers, variants)
    create_orders(customers)
    print("Database population complete.")


if __name__ == "__main__":
    main()