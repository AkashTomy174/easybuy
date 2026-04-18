from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import Category, SubCategory
from user.models import OrderItem
from seller.models import SellerProfile, Product
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
    DISCOUNT_TYPE = Discount.DISCOUNT_TYPE

    name = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPE, default="PERCENT"
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.IntegerField()
    used_count = models.IntegerField(default=0)
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    is_active = models.BooleanField(default=True)
    seller = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promo_codes",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promo_codes",
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promo_codes",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promo_codes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code

    @property
    def scope_label(self):
        if self.product_id:
            return "Product"
        if self.subcategory_id:
            return "Subcategory"
        if self.category_id:
            return "Category"
        return "Unassigned"

    @property
    def target_name(self):
        if self.product_id:
            return self.product.name
        if self.subcategory_id:
            return self.subcategory.name
        if self.category_id:
            return self.category.name
        return ""

    def matches_product(self, product):
        if self.product_id:
            return product.id == self.product_id
        if self.subcategory_id:
            return product.subcategory_id == self.subcategory_id
        if self.category_id:
            subcategory = getattr(product, "subcategory", None)
            if subcategory is None:
                return False
            return subcategory.category_id == self.category_id
        return False

    def is_currently_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_to and self.valid_to < now:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, eligible_subtotal):
        eligible_subtotal = Decimal(eligible_subtotal or 0)
        if eligible_subtotal <= 0:
            return Decimal("0.00")

        if self.discount_type == "PERCENT":
            discount = eligible_subtotal * (self.discount_value / Decimal("100"))
        else:
            discount = self.discount_value

        return min(discount, eligible_subtotal)

    def clean(self):
        targets = [self.category_id, self.subcategory_id, self.product_id]
        if sum(bool(target) for target in targets) != 1:
            raise ValidationError("Select exactly one target: category, subcategory, or product.")

        if self.discount_value <= 0:
            raise ValidationError("Discount value must be greater than zero.")

        if self.discount_type == "PERCENT" and self.discount_value > 100:
            raise ValidationError("Percentage discounts cannot exceed 100%.")

        if self.usage_limit < 0 or self.used_count < 0:
            raise ValidationError("Usage counts cannot be negative.")

        if self.valid_to <= self.valid_from:
            raise ValidationError("Expiry must be after the start date.")

        if self.seller_id:
            if not self.product_id:
                raise ValidationError("Seller promo codes can only target a product.")
            if self.product and self.product.seller_id != self.seller_id:
                raise ValidationError("Sellers can only create promo codes for their own products.")
        elif self.product_id:
            raise ValidationError("Product promo codes must belong to a seller.")

        if self.subcategory_id and self.category_id:
            raise ValidationError("Choose either a category or a subcategory, not both.")

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        if not self.name:
            self.name = self.code
        self.full_clean()
        super().save(*args, **kwargs)
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

