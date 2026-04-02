from django.core.management.base import BaseCommand
from easybuy.seller.models import Product, ProductVariant, ProductImage
from easybuy.user.models import Order, OrderItem, Cart, CartItem
from easybuy.core.models import User, Address
from decimal import Decimal
import random
from datetime import datetime, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Adds product images and sample orders'

    def handle(self, *args, **kwargs):
        add_images_and_orders()

def add_images_and_orders():
    print("Adding product images and orders...")
    
    # Add Product Images
    print("\n1. Adding Product Images...")
    variants = ProductVariant.objects.all()
    
    # Sample image URLs (placeholder images)
    image_urls = [
        'https://via.placeholder.com/500x500/4a7c43/ffffff?text=Product+1',
        'https://via.placeholder.com/500x500/ff7f50/ffffff?text=Product+2',
        'https://via.placeholder.com/500x500/0ea5e9/ffffff?text=Product+3',
        'https://via.placeholder.com/500x500/10b981/ffffff?text=Product+4',
        'https://via.placeholder.com/500x500/f59e0b/ffffff?text=Product+5',
    ]
    
    for idx, variant in enumerate(variants):
        # Check if images already exist
        if variant.images.count() == 0:
            # Add 2-3 images per variant
            for i in range(random.randint(2, 3)):
                ProductImage.objects.create(
                    variant=variant,
                    alt_text=f"{variant.product.name} - Image {i+1}",
                    is_primary=(i == 0)
                )
            print(f"[OK] Added images for: {variant.product.name}")
    
    # Create Orders
    print("\n2. Creating Sample Orders...")
    customers = User.objects.filter(role='CUSTOMER')
    
    if not customers.exists():
        print("[SKIP] No customers found")
        return
    
    for customer in customers:
        address = Address.objects.filter(user=customer).first()
        if not address:
            print(f"[SKIP] No address for {customer.username}")
            continue
        
        # Create 2-3 orders per customer
        for order_num in range(random.randint(2, 3)):
            # Get random variants
            order_variants = random.sample(list(variants), random.randint(1, 3))
            
            # Calculate total
            total = Decimal('0.00')
            items_data = []
            
            for variant in order_variants:
                quantity = random.randint(1, 2)
                subtotal = variant.selling_price * quantity
                total += subtotal
                items_data.append({
                    'variant': variant,
                    'quantity': quantity,
                    'price': variant.selling_price
                })
            
            # Create order
            order = Order.objects.create(
                user=customer,
                order_number=f'ORD{timezone.now().strftime("%Y%m%d")}{random.randint(1000, 9999)}',
                total_amount=total,
                shipping_name=address.full_name,
                shipping_phone=address.phone_number,
                shipping_address=f"{address.house_info}, {address.locality}, {address.city}, {address.state} - {address.pincode}",
                order_status=random.choice(['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']),
                payment_status=random.choice(['PENDING', 'COMPLETED', 'FAILED'])
            )
            
            # Create order items
            for item_data in items_data:
                OrderItem.objects.create(
                    order=order,
                    variant=item_data['variant'],
                    seller=item_data['variant'].product.seller,
                    quantity=item_data['quantity'],
                    price_at_purchase=item_data['price'],
                    status=random.choice(['PENDING', 'SHIPPED', 'DELIVERED'])
                )
            
            print(f"[OK] Created order {order.order_number} for {customer.username}")
    
    # Create Cart Items
    print("\n3. Creating Cart Items...")
    for customer in customers:
        cart, _ = Cart.objects.get_or_create(user=customer)
        
        # Add 1-2 items to cart
        if cart.items.count() == 0:
            cart_variants = random.sample(list(variants), min(random.randint(1, 2), len(variants)))
            for variant in cart_variants:
                CartItem.objects.create(
                    cart=cart,
                    variant=variant,
                    quantity=random.randint(1, 2),
                    price_at_time=variant.selling_price
                )
            print(f"[OK] Added cart items for {customer.username}")
    
    print("\n" + "="*50)
    print("IMAGES AND ORDERS ADDED SUCCESSFULLY!")
    print("="*50)
    print("\nSummary:")
    print(f"- Product Images: {ProductImage.objects.count()}")
    print(f"- Orders: {Order.objects.count()}")
    print(f"- Order Items: {OrderItem.objects.count()}")
    print(f"- Cart Items: {CartItem.objects.count()}")
    print("\n" + "="*50)
