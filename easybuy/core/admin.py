# trunk-ignore-all(isort)
from django.contrib import admin

from .models import User, Banner, Category, SubCategory, Address, Notification, Otp


# Register your models here.
admin.site.register(User)
admin.site.register(Address)
admin.site.register(Notification)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Banner)
admin.site.register(Otp)
