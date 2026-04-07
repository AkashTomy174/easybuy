from django.contrib import admin

from .models import (
    ChatMessage,
    ChatSession,
    ComplaintReplyTemplate,
    ComplaintTicket,
    EscalationLog,
    FAQEntry,
)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "session_key")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "intent", "created_at")
    list_filter = ("role", "intent")
    search_fields = ("content",)


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "priority", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer", "keywords")


@admin.register(ComplaintReplyTemplate)
class ComplaintReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ("category", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("category", "reply_text")


@admin.register(ComplaintTicket)
class ComplaintTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "severity", "status", "created_at")
    list_filter = ("category", "severity", "status")
    search_fields = ("subject", "description", "user__username", "order__order_number")


@admin.register(EscalationLog)
class EscalationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "session", "reason", "created_at")
    search_fields = ("reason",)

