# trunk-ignore-all(isort)
from django.contrib import admin

from .models import (
    User,
    Banner,
    Category,
    SubCategory,
    Address,
    Notification,
    Otp,
    NotificationConfig,
    NotificationDelivery,
    AdSpace,
    AdBooking,
)


# Register your models here.
admin.site.register(User)
admin.site.register(Address)
admin.site.register(Notification)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Banner)
admin.site.register(Otp)
admin.site.register(NotificationDelivery)
admin.site.register(NotificationConfig)


@admin.register(AdSpace)
class AdSpaceAdmin(admin.ModelAdmin):
    list_display = ["name", "price_per_day", "is_active"]


admin.site.register(AdBooking)
