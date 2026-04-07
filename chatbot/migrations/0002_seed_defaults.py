from django.db import migrations


FAQ_DEFAULTS = [
    {
        "question": "What is your return policy?",
        "answer": "Most returnable products can be returned within the product's stated return window after delivery. I can also help you check return eligibility for one of your orders.",
        "category": "returns",
        "keywords": "return, refund, replacement, damaged, exchange",
        "priority": 10,
    },
    {
        "question": "How long does shipping take?",
        "answer": "Shipping time depends on the product and seller, but once an order is confirmed you can track the latest status from your orders page.",
        "category": "shipping",
        "keywords": "shipping, delivery, ship, arrive, courier",
        "priority": 9,
    },
    {
        "question": "What payment methods do you support?",
        "answer": "You can currently check out with online payment or Cash on Delivery, depending on availability for the order.",
        "category": "payments",
        "keywords": "payment, cod, card, upi, online payment",
        "priority": 8,
    },
    {
        "question": "How do I cancel an order?",
        "answer": "You can cancel eligible items from your orders page before they are shipped or delivered. If you want, I can guide you to your latest order status first.",
        "category": "orders",
        "keywords": "cancel, cancellation, order cancel",
        "priority": 8,
    },
    {
        "question": "How do I contact support?",
        "answer": "You can tell me about the issue here and I can raise a complaint ticket for you. You can also ask me to talk to support or escalate a problem.",
        "category": "complaints",
        "keywords": "support, complaint, issue, problem, help",
        "priority": 7,
    },
]

COMPLAINT_TEMPLATE_DEFAULTS = {
    "damaged_product": "I'm sorry your product arrived damaged. I've created a complaint ticket so the support team can review it quickly. If this is tied to an order, keep photos ready in case the team asks for them.",
    "late_delivery": "I'm sorry your order is taking longer than expected. I've logged this as a delivery complaint and the support team can review the shipment status.",
    "wrong_product": "I'm sorry you received the wrong item. I've created a complaint ticket so the team can help with the next steps.",
    "refund_issue": "I'm sorry you're having trouble with the refund process. I've raised a complaint ticket so support can investigate.",
    "general": "I'm sorry you're dealing with this. I've created a support ticket so the team can follow up.",
}


def seed_defaults(apps, schema_editor):
    FAQEntry = apps.get_model("chatbot", "FAQEntry")
    ComplaintReplyTemplate = apps.get_model("chatbot", "ComplaintReplyTemplate")

    for faq in FAQ_DEFAULTS:
        FAQEntry.objects.get_or_create(question=faq["question"], defaults=faq)

    for category, reply_text in COMPLAINT_TEMPLATE_DEFAULTS.items():
        ComplaintReplyTemplate.objects.get_or_create(
            category=category, defaults={"reply_text": reply_text, "is_active": True}
        )


def remove_defaults(apps, schema_editor):
    FAQEntry = apps.get_model("chatbot", "FAQEntry")
    ComplaintReplyTemplate = apps.get_model("chatbot", "ComplaintReplyTemplate")

    FAQEntry.objects.filter(question__in=[faq["question"] for faq in FAQ_DEFAULTS]).delete()
    ComplaintReplyTemplate.objects.filter(
        category__in=list(COMPLAINT_TEMPLATE_DEFAULTS.keys())
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, remove_defaults),
    ]
