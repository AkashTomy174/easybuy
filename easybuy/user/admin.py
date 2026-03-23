from django.contrib import admin
from .models import NotificationPreference, SavedCard


# Register your models here.
@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "email_order_updates",
        "whatsapp_order_updates",
        "updated_at",
    ]
    list_filter = ["email_order_updates", "whatsapp_order_updates"]
    search_fields = ["user__username", "user__email"]


@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "card_holder_name",
        "card_brand",
        "card_number",
        "is_default",
    ]
    search_fields = ["user__username", "card_holder_name"]
