from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    title = models.CharField(max_length=120, default="Shopping Assistant")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"ChatSession #{self.pk}"


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("bot", "Bot"),
        ("system", "System"),
    )

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class FAQEntry(models.Model):
    CATEGORY_CHOICES = (
        ("shipping", "Shipping"),
        ("returns", "Returns"),
        ("payments", "Payments"),
        ("orders", "Orders"),
        ("complaints", "Complaints"),
        ("account", "Account"),
        ("general", "General"),
    )

    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")
    keywords = models.TextField(blank=True, help_text="Comma-separated keywords")
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "question"]

    def __str__(self):
        return self.question


class ComplaintReplyTemplate(models.Model):
    category = models.CharField(max_length=30, unique=True)
    reply_text = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.category


class ComplaintTicket(models.Model):
    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("ESCALATED", "Escalated"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
    )
    SEVERITY_CHOICES = (
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="complaint_tickets",
        null=True,
        blank=True,
    )
    chat_session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        related_name="complaints",
        null=True,
        blank=True,
    )
    order = models.ForeignKey(
        "user.Order",
        on_delete=models.SET_NULL,
        related_name="complaint_tickets",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=30, default="other")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    bot_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ticket #{self.pk} - {self.subject}"


class EscalationLog(models.Model):
    ticket = models.ForeignKey(
        ComplaintTicket,
        on_delete=models.CASCADE,
        related_name="escalations",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="escalations",
    )
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Escalation #{self.pk}"

