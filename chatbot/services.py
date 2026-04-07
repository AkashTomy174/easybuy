import json
import logging
import re
from types import SimpleNamespace

from django.conf import settings
from django.db.models import Q
from django.urls import reverse

from core.models import Notification
from seller.models import ProductVariant
from user.models import Order

from .models import ComplaintReplyTemplate, ComplaintTicket, FAQEntry

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised via configuration fallback
    OpenAI = None


logger = logging.getLogger(__name__)


DEFAULT_FAQS = [
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

DEFAULT_COMPLAINT_TEMPLATES = {
    "damaged_product": "I'm sorry your product arrived damaged. I've created a complaint ticket so the support team can review it quickly. If this is tied to an order, keep photos ready in case the team asks for them.",
    "late_delivery": "I'm sorry your order is taking longer than expected. I've logged this as a delivery complaint and the support team can review the shipment status.",
    "wrong_product": "I'm sorry you received the wrong item. I've created a complaint ticket so the team can help with the next steps.",
    "refund_issue": "I'm sorry you're having trouble with the refund process. I've raised a complaint ticket so support can investigate.",
    "general": "I'm sorry you're dealing with this. I've created a support ticket so the team can follow up.",
}

STOP_WORDS = {
    "a",
    "an",
    "the",
    "for",
    "to",
    "of",
    "in",
    "on",
    "at",
    "i",
    "me",
    "my",
    "you",
    "your",
    "it",
    "this",
    "that",
    "what",
    "how",
    "do",
    "does",
    "can",
    "could",
    "would",
    "should",
    "is",
    "are",
    "am",
    "be",
    "show",
    "find",
    "need",
    "want",
    "looking",
    "tell",
    "about",
    "something",
    "sure",
    "please",
    "with",
    "and",
    "or",
    "under",
    "below",
    "best",
    "product",
    "products",
}

PRODUCT_HINTS = {
    "phone",
    "mobile",
    "laptop",
    "headphone",
    "headphones",
    "earbuds",
    "tv",
    "tablet",
    "camera",
    "watch",
    "speaker",
    "buy",
    "recommend",
    "recommendation",
    "browse",
}

ORDER_HINTS = {"order", "track", "delivery", "shipped", "delivered", "cancel"}
COMPLAINT_HINTS = {
    "complaint",
    "issue",
    "problem",
    "damaged",
    "broken",
    "refund",
    "late",
    "delay",
    "wrong",
    "support",
}
ESCALATION_HINTS = {"human", "agent", "support person", "representative"}

AI_SYSTEM_PROMPT = """
You are EasyBuy's shopping and support assistant.
Reply in valid JSON only.

Rules:
- Only use facts from the supplied context.
- Never invent policies, refunds, order statuses, stock, prices, or delivery promises.
- Do not say a complaint ticket was created unless the context explicitly says so.
- If the context is not enough, say that briefly and ask one clear follow-up question.
- Keep the answer concise and helpful.

Return a JSON object with:
- reply: string
- intent: string
- quick_replies: array of up to 3 short strings
- should_escalate: boolean
""".strip()


def tokenize(message):
    return re.findall(r"[a-zA-Z0-9]+", (message or "").lower())


def get_quick_replies(user):
    options = [
        "Show budget phones",
        "What is your return policy?",
        "How long does shipping take?",
        "I have a complaint",
    ]
    if getattr(user, "is_authenticated", False):
        options.insert(0, "Track my latest order")
    return options


def get_welcome_message(user):
    if getattr(user, "is_authenticated", False):
        return (
            f"Hi {user.first_name or user.username}, I'm your EasyBuy assistant. "
            "I can help you browse products, answer store questions, check your orders, and log complaints."
        )
    return (
        "Hi, I'm your EasyBuy assistant. I can help you browse products, answer FAQs, and log support issues."
    )


def openai_enabled():
    return bool(
        getattr(settings, "OPENAI_ENABLED", False)
        and getattr(settings, "OPENAI_API_KEY", "").strip()
        and OpenAI is not None
    )


def get_openai_client():
    if not openai_enabled():
        return None
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=getattr(settings, "OPENAI_TIMEOUT_SECONDS", 20),
    )


def _contains_keyword(message, keyword):
    lower_message = (message or "").lower()
    if " " in keyword:
        return keyword in lower_message
    return keyword in set(tokenize(lower_message))


def _faq_entries():
    entries = list(FAQEntry.objects.filter(is_active=True))
    if entries:
        return entries
    return [SimpleNamespace(**entry) for entry in DEFAULT_FAQS]


def _relevant_faq_context(message, limit=3):
    tokens = {token for token in tokenize(message) if token not in STOP_WORDS}
    scored_entries = []

    for entry in _faq_entries():
        haystack = (
            f"{entry.question} {getattr(entry, 'keywords', '')} {entry.answer}"
        ).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored_entries.append((score + getattr(entry, "priority", 0), entry))

    scored_entries.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "question": entry.question,
            "answer": entry.answer,
            "category": getattr(entry, "category", "general"),
        }
        for _, entry in scored_entries[:limit]
    ]


def match_faq(message):
    tokens = {token for token in tokenize(message) if token not in STOP_WORDS}
    best_entry = None
    best_score = 0

    for entry in _faq_entries():
        haystack = f"{entry.question} {getattr(entry, 'keywords', '')}".lower()
        token_score = sum(1 for token in tokens if token in haystack)
        if token_score == 0 and entry.question.lower() not in (message or "").lower():
            continue

        score = token_score * 5
        if entry.question.lower() in (message or "").lower():
            score += 3
        score += getattr(entry, "priority", 0)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry and best_score >= 3:
        return best_entry
    return None


def parse_budget(message):
    budget_patterns = [
        r"(?:under|below|less than)\s*(?:rs\.?|inr)?\s*(\d+)",
        r"(?:rs\.?|inr)\s*(\d+)",
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, (message or "").lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None


def is_product_query(message):
    tokens = set(tokenize(message))
    return bool(tokens.intersection(PRODUCT_HINTS)) or bool(parse_budget(message))


def _base_product_queryset():
    return (
        ProductVariant.objects.filter(
            product__is_active=True,
            product__approval_status="APPROVED",
            product__seller__status="APPROVED",
        )
        .select_related(
            "product",
            "product__seller",
            "product__subcategory",
            "product__subcategory__category",
        )
        .prefetch_related("images")
    )


def _product_image_url(variant):
    primary = next(
        (image for image in variant.images.all() if image.is_primary and image.image),
        None,
    )
    primary = primary or next(
        (image for image in variant.images.all() if image.image),
        None,
    )
    return primary.image.url if primary and primary.image else ""


def serialize_product(variant):
    return {
        "id": variant.id,
        "name": variant.product.name,
        "brand": variant.product.brand,
        "price": str(variant.selling_price),
        "mrp": str(variant.mrp),
        "stock_quantity": variant.stock_quantity,
        "url": reverse("product_detail_user", args=[variant.product.slug]),
        "image_url": _product_image_url(variant),
    }


def search_products(message):
    raw_tokens = [
        token
        for token in tokenize(message)
        if token not in STOP_WORDS and not token.isdigit()
    ]
    tokens = []
    for token in raw_tokens:
        tokens.append(token)
        if token.endswith("s") and len(token) > 3:
            tokens.append(token[:-1])
    budget = parse_budget(message)

    queryset = _base_product_queryset()
    if budget:
        queryset = queryset.filter(selling_price__lte=budget)

    if tokens:
        query = Q()
        for token in tokens:
            query |= Q(product__name__icontains=token)
            query |= Q(product__brand__icontains=token)
            query |= Q(product__subcategory__name__icontains=token)
            query |= Q(product__subcategory__category__name__icontains=token)
        queryset = queryset.filter(query)

    variants = list(queryset.order_by("selling_price", "-created_at")[:5])
    return variants, budget


def _recent_product_context(message, limit=3):
    if not is_product_query(message):
        return []
    variants, budget = search_products(message)
    return {
        "budget": budget,
        "products": [serialize_product(variant) for variant in variants[:limit]],
    }


def _extract_order_number(message):
    match = re.search(r"\b(EB[0-9]{8}[A-Za-z0-9]+|ORD-[A-Za-z0-9-]+)\b", message or "")
    return match.group(1) if match else None


def _recent_order_context(user, limit=2):
    if not getattr(user, "is_authenticated", False):
        return []

    orders = (
        Order.objects.filter(user=user)
        .prefetch_related("items__variant__product")
        .order_by("-ordered_at")[:limit]
    )
    context = []
    for order in orders:
        context.append(
            {
                "order_number": order.order_number,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "items": [item.variant.product.name for item in order.items.all()[:3]],
            }
        )
    return context


def order_help_response(user, message):
    if not getattr(user, "is_authenticated", False):
        return {
            "reply": "Please log in so I can check your orders securely.",
            "intent": "order_status",
            "quick_replies": ["What is your return policy?", "I have a complaint"],
        }

    orders = (
        Order.objects.filter(user=user)
        .prefetch_related("items__variant__product")
        .order_by("-ordered_at")
    )
    order_number = _extract_order_number(message)
    if order_number:
        orders = orders.filter(order_number__iexact=order_number)

    order = orders.first()
    if not order:
        return {
            "reply": "I couldn't find a matching order from your account. You can share the order number or check your Orders page.",
            "intent": "order_status",
            "quick_replies": ["Track my latest order", "I have a complaint"],
        }

    item_summaries = [
        f"{item.variant.product.name}: {item.status}"
        for item in order.items.all()[:3]
    ]
    reply = (
        f"Your latest order {order.order_number} is currently {order.order_status.lower()} "
        f"with payment status {order.payment_status.lower()}."
    )
    if item_summaries:
        reply += " Item update: " + "; ".join(item_summaries) + "."
    return {
        "reply": reply,
        "intent": "order_status",
        "quick_replies": ["What is your return policy?", "I have a complaint"],
        "meta": {"order_number": order.order_number},
    }


def detect_complaint_category(message):
    mapping = {
        "damaged_product": ["damaged", "broken", "defect"],
        "late_delivery": ["late", "delay", "not arrived", "not delivered"],
        "wrong_product": ["wrong item", "wrong product", "different item"],
        "refund_issue": ["refund", "money back", "reversal"],
    }
    for category, keywords in mapping.items():
        if any(_contains_keyword(message, keyword) for keyword in keywords):
            return category
    return "general"


def detect_severity(message):
    if any(_contains_keyword(message, word) for word in ["fraud", "urgent", "angry", "worst", "legal"]):
        return "HIGH"
    if any(_contains_keyword(message, word) for word in ["damaged", "refund", "wrong", "delay"]):
        return "MEDIUM"
    return "LOW"


def _recent_chat_context(session, limit=6):
    if not session:
        return []
    messages = session.messages.order_by("-created_at")[:limit]
    return [
        {
            "role": chat_message.role,
            "content": chat_message.content,
            "intent": chat_message.intent,
        }
        for chat_message in reversed(list(messages))
    ]


def _complaint_template(category):
    template = ComplaintReplyTemplate.objects.filter(
        category=category, is_active=True
    ).first()
    if template:
        return template.reply_text
    return DEFAULT_COMPLAINT_TEMPLATES.get(
        category, DEFAULT_COMPLAINT_TEMPLATES["general"]
    )


def build_ai_context(user, session, message, extra_context=None):
    context = {
        "capabilities": [
            "answer store FAQs",
            "browse products from the catalog",
            "help logged-in users with their own orders",
            "guide users to returns and complaints",
        ],
        "relevant_faqs": _relevant_faq_context(message),
        "recent_products": _recent_product_context(message),
        "recent_orders": _recent_order_context(user),
        "recent_messages": _recent_chat_context(session),
    }
    if extra_context:
        context["extra"] = extra_context
    return context


def _normalize_ai_reply(user, data):
    if not isinstance(data, dict):
        return None

    reply = str(data.get("reply", "")).strip()
    if not reply:
        return None

    quick_replies = [
        str(item).strip()
        for item in data.get("quick_replies", [])
        if str(item).strip()
    ][:3]
    if not quick_replies:
        quick_replies = get_quick_replies(user)[:3]

    intent = str(data.get("intent", "ai_fallback")).strip() or "ai_fallback"
    if not intent.startswith("ai_"):
        intent = "ai_fallback"

    should_escalate = bool(data.get("should_escalate"))
    if should_escalate:
        quick_replies = list(
            dict.fromkeys(quick_replies + ["I have a complaint", "Talk to support"])
        )[:3]

    return {
        "reply": reply,
        "intent": intent,
        "quick_replies": quick_replies,
        "meta": {
            "source": "openai",
            "model": getattr(settings, "OPENAI_MODEL", ""),
            "should_escalate": should_escalate,
        },
    }


def generate_ai_reply(user, session, message, extra_context=None):
    client = get_openai_client()
    if not client:
        return None

    payload = {
        "user_message": message,
        "context": build_ai_context(
            user=user,
            session=session,
            message=message,
            extra_context=extra_context,
        ),
    }

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
            text={"format": {"type": "json_object"}},
            store=False,
        )
    except Exception:  # pragma: no cover - network/provider failures are logged
        logger.exception("OpenAI chatbot fallback failed.")
        return None

    if getattr(response, "status", "") == "incomplete":
        logger.warning("OpenAI chatbot response was incomplete.")
        return None

    raw_text = (getattr(response, "output_text", "") or "").strip()
    if not raw_text:
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("OpenAI chatbot response did not return valid JSON.")
        return None

    return _normalize_ai_reply(user, data)


def create_complaint(user, session, message):
    order = None
    if getattr(user, "is_authenticated", False):
        order_number = _extract_order_number(message)
        if order_number:
            order = Order.objects.filter(
                user=user, order_number__iexact=order_number
            ).first()

    category = detect_complaint_category(message)
    severity = detect_severity(message)
    subject = f"{category.replace('_', ' ').title()} complaint"
    reply = _complaint_template(category)

    ticket = ComplaintTicket.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        chat_session=session,
        order=order,
        category=category,
        severity=severity,
        subject=subject,
        description=message,
        bot_response=reply,
        status="ESCALATED" if severity == "HIGH" else "OPEN",
    )

    if getattr(user, "is_authenticated", False):
        Notification.objects.create(
            user=user,
            type="support_ticket",
            title="Support ticket created",
            message=f"Your support ticket #{ticket.id} has been created.",
        )

    return ticket, reply


def escalate_to_human(session, latest_ticket=None):
    from .models import EscalationLog

    reason = "User requested human support"
    EscalationLog.objects.create(ticket=latest_ticket, session=session, reason=reason)
    if latest_ticket and latest_ticket.status == "OPEN":
        latest_ticket.status = "ESCALATED"
        latest_ticket.save(update_fields=["status", "updated_at"])

    return {
        "reply": "I've marked this for human follow-up. A support team member can review the conversation and ticket details next.",
        "intent": "human_support",
        "quick_replies": ["Track my latest order", "What is your return policy?"],
    }


def handle_chat_message(user, session, message):
    clean_message = (message or "").strip()
    if not clean_message:
        return {
            "reply": "Tell me what you need help with. You can ask about products, orders, returns, payments, or complaints.",
            "intent": "empty",
            "quick_replies": get_quick_replies(user),
        }

    lower_message = clean_message.lower()
    if any(_contains_keyword(lower_message, phrase) for phrase in ESCALATION_HINTS):
        latest_ticket = session.complaints.order_by("-created_at").first()
        return escalate_to_human(session, latest_ticket)

    if any(_contains_keyword(lower_message, word) for word in COMPLAINT_HINTS):
        ticket, reply = create_complaint(user, session, clean_message)
        return {
            "reply": f"{reply} Your ticket number is #{ticket.id}.",
            "intent": "complaint",
            "quick_replies": ["Track my latest order", "How do returns work?"],
            "meta": {"ticket_id": ticket.id, "status": ticket.status},
        }

    if any(_contains_keyword(lower_message, word) for word in ORDER_HINTS):
        return order_help_response(user, clean_message)

    faq_entry = match_faq(clean_message)
    if faq_entry:
        return {
            "reply": faq_entry.answer,
            "intent": "faq",
            "quick_replies": get_quick_replies(user),
            "meta": {"faq_question": faq_entry.question},
        }

    if is_product_query(clean_message):
        variants, budget = search_products(clean_message)
        if variants:
            reply = "Here are some products you can look at"
            if budget:
                reply += f" under Rs. {budget}"
            reply += "."
            return {
                "reply": reply,
                "intent": "product_search",
                "products": [serialize_product(variant) for variant in variants],
                "quick_replies": [
                    "Show laptops",
                    "Show headphones",
                    "What is your return policy?",
                ],
            }
        ai_response = generate_ai_reply(
            user,
            session,
            clean_message,
            extra_context={
                "product_search_attempt": {
                    "budget": budget,
                    "matched_products": [],
                }
            },
        )
        if ai_response:
            return ai_response
        return {
            "reply": "I couldn't find a strong match yet. Try telling me the category, brand, or a budget like 'phones under 15000'.",
            "intent": "product_search",
            "quick_replies": ["Show budget phones", "Show laptops", "Show headphones"],
        }

    ai_response = generate_ai_reply(user, session, clean_message)
    if ai_response:
        return ai_response

    return {
        "reply": (
            "I can help with product browsing, store questions, orders, returns, and complaints. "
            "Try asking something like 'show phones under 15000', 'track my order', or 'I have a complaint'."
        ),
        "intent": "fallback",
        "quick_replies": get_quick_replies(user),
    }
