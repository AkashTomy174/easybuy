from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.contrib.auth.hashers import check_password, make_password


def generate_unique_category_slug(klass, field, slug_field="slug"):
    origin_slug = slugify(field)
    unique_slug = origin_slug
    counter = 1
    while klass.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{origin_slug}-{counter}"
        counter += 1
    return unique_slug


class User(AbstractUser):
    ROLE_ADMIN = "ADMIN"
    ROLE_SELLER = "SELLER"
    ROLE_CUSTOMER = "CUSTOMER"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_SELLER, "Seller"),
        (ROLE_CUSTOMER, "Customer"),
    )

    GENDER_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    )

    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER
    )
    profile_image = models.ImageField(
        upload_to="profile_images/", null=True, blank=True
    )

    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ACTION_PERMISSIONS = {
        ROLE_ADMIN: {
            "admin:access",
            "catalog:approve",
            "catalog:manage",
            "seller:review",
        },
        ROLE_SELLER: {
            "seller:access",
            "seller:inventory",
            "seller:orders",
            "seller:products",
            "seller:promotions",
            "seller:returns",
            "seller:reviews",
        },
        ROLE_CUSTOMER: {
            "customer:access",
            "customer:cart",
            "customer:checkout",
            "customer:orders",
            "customer:reviews",
            "customer:wishlist",
        },
    }

    def __str__(self):
        return self.username

    def has_role(self, *roles):
        return self.role in roles

    def has_permission(self, action):
        if not action:
            return True
        return action in self.ACTION_PERMISSIONS.get(self.role, set())


class Otp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp")
    otp = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.email}"

    def save(self, *args, **kwargs):
        if self.otp and not self.otp.startswith("pbkdf2_"):
            self.otp = make_password(self.otp)
        super().save(*args, **kwargs)

    def matches(self, raw_otp):
        if not raw_otp:
            return False
        return check_password(raw_otp, self.otp)


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    pincode = models.CharField(max_length=10)
    locality = models.CharField(max_length=255)
    house_info = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    landmark = models.CharField(max_length=255, blank=True)
    address_type = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    message = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    redirect_url = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "-created_at"]),
        ]


class NotificationDelivery(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries"
    )
    channel = models.CharField(
        max_length=20,
        choices=[
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("in_app", "In App"),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    sent_at = models.DateTimeField(null=True, blank=True)


class NotificationConfig(models.Model):
    type = models.CharField(max_length=50, unique=True)

    enable_email = models.BooleanField(default=True)
    enable_whatsapp = models.BooleanField(default=False)
    enable_in_app = models.BooleanField(default=True)


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    image_url = models.ImageField(upload_to="Category/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="subcategories"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_category_slug(SubCategory, self.name)
        super().save(*args, **kwargs)


class Banner(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="banners/", blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    redirect_url = models.URLField(blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "start_date", "end_date"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return self.title

    @property
    def hero_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class StockNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stock_notifications")
    variant = models.ForeignKey("seller.ProductVariant", on_delete=models.CASCADE, related_name="notifications")
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "variant"]

    def __str__(self):
        return f"{self.user.username} - {self.variant}"
