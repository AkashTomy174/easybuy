from django.db import models
from easybuy.core.models import User
from easybuy.seller.models import ProductVariant, SellerProfile, Product


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    wishlist_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField()
    comment = models.TextField()
    seller_reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['user', 'product']),
            models.Index(fields=['product', '-helpful_count']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name='rating_range'
            )
        ]


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="reviews/images/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']


class ReviewVideo(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="videos")
    video = models.FileField(upload_to="reviews/videos/")
    thumbnail = models.ImageField(upload_to="reviews/thumbnails/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']


class ReviewHelpful(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="review_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['review', 'user']
        indexes = [
            models.Index(fields=['review', 'user']),
        ]


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20)
    order_status = models.CharField(max_length=20)
    shipping_name = models.CharField(max_length=100, null=True, blank=True)
    shipping_phone = models.CharField(max_length=15, null=True, blank=True)
    shipping_address = models.TextField(null=True, blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    CHOICES=(
        ("SHIPPED","approved"),
        ("PENDING","pending"),
        ("CANCELLED","rejected"),
        ("RETURNED","returned")
    )
    status=models.CharField(max_length=50,choices=CHOICES,default="PENDING")
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)


class PaymentTransaction(models.Model):
    order = models.ForeignKey(
        "Order", on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_id = models.CharField(max_length=255)
    payment_gateway = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    gateway_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReturnRequest(models.Model):
    order_item = models.ForeignKey(
        "OrderItem", on_delete=models.CASCADE, related_name="return_requests"
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, default="PENDING")
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class Shipment(models.Model):
    order = models.ForeignKey(
        "Order", on_delete=models.CASCADE, related_name="shipments"
    )
    tracking_number = models.CharField(max_length=100)
    courier_name = models.CharField(max_length=100)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)
