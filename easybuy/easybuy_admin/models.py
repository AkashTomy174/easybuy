from django.db import models
from easybuy.core.models import Category
from easybuy.user.models import OrderItem
from easybuy.seller.models import SellerProfile, Product
# Create your models here.


class AdminProfile(models.Model):
    user = models.OneToOneField("core.User", on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    
class Offer(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.title
class Discount(models.Model):
    DISCOUNT_TYPE = (
        ('PERCENT', 'Percentage'),
        ('FLAT', 'Flat'),
    )
    name = models.CharField(max_length=100)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return self.name
    
    
    
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.IntegerField()
    used_count = models.IntegerField(default=0)
    def __str__(self):
        return self.code
class OfferDiscountBridge(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.offer)
    
    
class ProductOfferBridge(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.product)
    
class CategoryOfferBridge(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.category)
    
    
class ProductDiscountBridge(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.product)
    
    
class CategoryDiscountBridge(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.category)
    
    
    
class PlatformCommission(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SETTLED', 'Settled'),
    )
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    commission_percentage = models.FloatField()
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    settlement_status = models.CharField(max_length=20,choices=STATUS_CHOICES, default='PENDING')
    settled_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return str(self.seller)
