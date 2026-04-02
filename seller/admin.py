from django.contrib import admin
from . models import SellerProfile,Product,ProductImage,ProductVariant,ProductRatingSummary,InventoryLog,Attribute,AttributeOption,VariantAttributeBridge

# Register your models here.
admin.site.register(SellerProfile)
admin.site.register(ProductRatingSummary)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(AttributeOption)
admin.site.register(ProductVariant)
admin.site.register(InventoryLog)
admin.site.register(Attribute)
admin.site.register(VariantAttributeBridge)
