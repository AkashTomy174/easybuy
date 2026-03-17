from easybuy.core.models import User, Category, SubCategory, Address
from easybuy.seller.models import SellerProfile, Product, ProductVariant
from easybuy.user.models import Cart, Order, OrderItem
from django.utils.text import slugify
from decimal import Decimal
import random
from django.utils import timezone

print("🗄️ Populating EasyBuy database...")

# 1. Admin
admin = User.objects.create_user(
    username="admin",
    email="admin@easybuy.com",
    password="921967",
    role="ADMIN",
    is_staff=True,
    is_superuser=True,
)
print("✅ Admin: admin/921967")

# 2. Sellers
sellers = []
seller_names = ["TechWorld", "FashionHub", "BookMart"]
for i, name in enumerate(seller_names):
    user = User.objects.create_user(
        username=f"seller{i+1}",
        email=f"seller{i+1}@easybuy.com",
        password="seller123",
        role="SELLER",
    )
    profile = SellerProfile.objects.create(
        user=user,
        store_name=name,
        store_slug=slugify(name),
        gst_number=f"GST{i+1}ABC1234567",
        pan_number=f"ABCDE{i+1}1234",
        bank_account_number=f"123456789{i+1}",
        ifsc_code="HDFC0001",
        business_address=f"Store #{i+1}, Mumbai",
        status="APPROVED",
    )
    sellers.append(profile.user)
print("✅ Sellers: seller1-3/seller123")

# 3. Customers
customers = []
for i in range(1, 3):
    user = User.objects.create_user(
        username=f"customer{i}",
        email=f"customer{i}@gmail.com",
        password="customer123",
        role="CUSTOMER",
    )
    customers.append(user)
print("✅ Customers: customer1-2/customer123")

# 4. Categories & Subcategories
cats = {
    "Electronics": ["Smartphones", "Laptops"],
    "Fashion": ["Men Clothing", "Women Clothing"],
    "Books": ["Fiction", "Non-Fiction"],
}
category_objs = {}
for cat_name, subs in cats.items():
    cat = Category.objects.create(name=cat_name, slug=slugify(cat_name), is_active=True)
    category_objs[cat_name] = cat
    for sub in subs:
        SubCategory.objects.create(
            name=sub, category=cat, slug=slugify(sub), is_active=True
        )
print("✅ Categories created")

# 5. Products & Variants
products = []
for i, (name, cat_name, sub_name, price, brand) in enumerate(
    [
        ("iPhone 15 Pro", "Electronics", "Smartphones", 129999, "Apple"),
        ("MacBook Pro", "Electronics", "Laptops", 199999, "Apple"),
        ("Levi's Shirt", "Fashion", "Men Clothing", 1299, "Levi's"),
        ("Zara Dress", "Fashion", "Women Clothing", 1999, "Zara"),
        ("Great Gatsby", "Books", "Fiction", 299, "Penguin"),
    ]
):
    seller = sellers[i % len(sellers)]
    cat = category_objs[cat_name]
    sub = SubCategory.objects.get(category=cat, name=sub_name)
    product = Product.objects.create(
        seller=SellerProfile.objects.get(user=seller),
        subcategory=sub,
        name=name,
        slug=slugify(name),
        description=f"Premium {name}",
        brand=brand,
        approval_status="APPROVED",
    )
    variant = ProductVariant.objects.create(
        product=product,
        sku_code=f"EBSKU{1000+i}",
        mrp=Decimal(str(price * 1.2)),
        selling_price=Decimal(str(price)),
        cost_price=Decimal(str(price * 0.7)),
        stock_quantity=random.randint(20, 100),
        tax_percentage=18.0,
    )
    products.append(variant)
print("✅ Products & variants created")

# 6. Addresses & Carts
for customer in customers:
    Address.objects.create(
        user=customer,
        full_name=f"{customer.first_name} {customer.last_name}",
        phone_number="9876543210",
        pincode="400001",
        locality="Downtown",
        house_info="Apt 101",
        city="Mumbai",
        state="Maharashtra",
        is_default=True,
    )
    Cart.objects.get_or_create(user=customer)
print("✅ Addresses & carts created")

# 7. Orders & OrderItems
for customer in customers:
    for _ in range(3):
        total = sum(Decimal(str(random.randint(1000, 50000) / 100)) for _ in range(2))
        order = Order.objects.create(
            user=customer,
            order_number=f"EB{random.randint(10000000,99999999)}",
            total_amount=total,
            payment_status="COMPLETED",
            order_status=random.choice(["DELIVERED", "SHIPPED"]),
            shipping_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Mumbai",
        )
        for _ in range(2):
            variant = random.choice(products)
            OrderItem.objects.create(
                order=order,
                seller=variant.product.seller.user.seller_profile,
                variant=variant,
                quantity=random.randint(1, 3),
                price_at_purchase=variant.selling_price,
            )
print("✅ Orders created")

print("\n🎉 DATABASE FULLY POPULATED!")
print("👤 Logins: admin/921967 | seller1/seller123 | customer1/customer123")
print("📱 Run: python manage.py runserver")
print("🌐 Visit: http://127.0.0.1:8000")
