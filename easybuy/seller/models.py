from django.db import models
from django.utils.text import slugify
from easybuy.core.models import User, SubCategory

# Create your models here.


def generate_unique_slug(klass, field, slug_field="slug"):
    origin_slug = slugify(field)
    unique_slug = origin_slug
    counter = 1
    while klass.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{origin_slug}-{counter}"
        counter += 1
    return unique_slug


class SellerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="seller_profile"
    )
    store_name = models.CharField(max_length=255)
    store_slug = models.SlugField(unique=True)
    gst_number = models.CharField(max_length=50)
    pan_number = models.CharField(max_length=50)
    bank_account_number = models.CharField(max_length=50)
    doc = models.FileField(upload_to="seller_documents/")
    ifsc_code = models.CharField(max_length=20)
    business_address = models.TextField()
    CHOICES = (
        ("APPROVED", "approved"),
        ("REJECTED", "rejected"),
        ("PENDING", "pending"),
    )
    status = models.CharField(max_length=20, choices=CHOICES, default="PENDING")
    rating = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store_name


class Product(models.Model):
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.CASCADE, related_name="products"
    )
    subcategory = models.ForeignKey(
        SubCategory, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100)
    is_cancellable = models.BooleanField(default=True)
    is_returnable = models.BooleanField(default=True)
    return_days = models.IntegerField(default=7)
    approval_status = models.CharField(max_length=20, default="PENDING")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Product, self.name)
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku_code = models.CharField(max_length=100, unique=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    weight = models.FloatField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    tax_percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.sku_code}"


class ProductImage(models.Model):
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/variants/", null=True, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.variant.sku_code} Image"


class Attribute(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class AttributeOption(models.Model):
    attribute = models.ForeignKey(
        Attribute, on_delete=models.CASCADE, related_name="options"
    )
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class VariantAttributeBridge(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    option = models.ForeignKey(AttributeOption, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.variant.sku_code} - {self.option}"


class InventoryLog(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    change_amount = models.IntegerField()
    reason = models.CharField(max_length=50)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProductRatingSummary(models.Model):
    product = models.OneToOneField("seller.Product", on_delete=models.CASCADE)
    average_rating = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
