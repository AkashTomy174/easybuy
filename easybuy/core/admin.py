from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Address, Notification, Category, SubCategory, Banner



class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    prepopulated_fields = {"slug": ("name",)}

class AddressInline(admin.StackedInline):
    model = Address
    extra = 0

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = ("username", "email", "phone_number", "role", "is_verified", "is_staff")
    list_filter = ("role", "is_verified", "is_staff")
    inlines = [AddressInline]
    
    fieldsets = UserAdmin.fieldsets + (
        ("EasyBuy Profile", {
            "fields": ("phone_number", "role", "profile_image", "is_verified")
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("EasyBuy Profile", {
            "fields": ("phone_number", "role", "profile_image", "is_verified")
        }),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [SubCategoryInline]

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("category", "is_active")
    search_fields = ("name",)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "city", "state", "address_type", "is_default")
    list_filter = ("city", "state", "address_type")
    search_fields = ("full_name", "phone_number", "user__username")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "message", "user__username")

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "start_date")
    search_fields = ("title",)