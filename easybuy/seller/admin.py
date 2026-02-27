from django.contrib import admin
from .models import SellerProfile, Product, ProductVariant, ProductImage,Attribute,AttributeOption,VariantAttributeBridge

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "is_verified", "rating")
    search_fields = ("store_name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "approval_status", "is_active", "created_at")
    list_filter = ("approval_status", "is_active")
    search_fields = ("name", "brand")
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3 
    fields = ('image', 'alt_text', 'is_primary')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku_code", "product", "selling_price", "stock_quantity")
    

    inlines = [ProductImageInline]
    
    search_fields = ("sku_code", "product__name")


admin.site.register(Attribute)
admin.site.register(AttributeOption)
admin.site.register(VariantAttributeBridge)