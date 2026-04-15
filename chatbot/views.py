import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import ChatMessage, ChatSession
from .services import get_quick_replies, get_welcome_message, handle_chat_message


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_chat_session(request, session_id=None):
    session_key = _ensure_session_key(request)
    queryset = ChatSession.objects.all()

    if request.user.is_authenticated:
        queryset = queryset.filter(user=request.user)
    else:
        queryset = queryset.filter(user__isnull=True, session_key=session_key)

    if session_id:
        chat_session = queryset.filter(pk=session_id).first()
        if chat_session:
            return chat_session

    if request.user.is_authenticated:
        chat_session = queryset.filter(is_active=True).first()
        if not chat_session:
            chat_session = ChatSession.objects.create(
                user=request.user, title="Shopping Assistant", is_active=True
            )
    else:
        chat_session = queryset.filter(is_active=True).first()
        if not chat_session:
            chat_session = ChatSession.objects.create(
                user=None,
                session_key=session_key,
                title="Shopping Assistant",
                is_active=True,
            )
    return chat_session


def _create_fresh_chat_session(request):
    session_key = _ensure_session_key(request)
    queryset = ChatSession.objects.all()

    if request.user.is_authenticated:
        queryset = queryset.filter(user=request.user)
        queryset.filter(is_active=True).update(is_active=False)
        return ChatSession.objects.create(
            user=request.user,
            title="Shopping Assistant",
            is_active=True,
        )

    queryset = queryset.filter(user__isnull=True, session_key=session_key)
    queryset.filter(is_active=True).update(is_active=False)
    return ChatSession.objects.create(
        user=None,
        session_key=session_key,
        title="Shopping Assistant",
        is_active=True,
    )


def _serialize_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "intent": message.intent,
        "payload": message.payload,
        "created_at": message.created_at.isoformat(),
    }


@require_POST
def start_session(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}

    new_session = bool(data.get("new_session"))
    chat_session = (
        _create_fresh_chat_session(request)
        if new_session
        else _get_chat_session(request)
    )
    if not chat_session.messages.exists():
        ChatMessage.objects.create(
            session=chat_session,
            role="bot",
            content=get_welcome_message(request.user),
            intent="welcome",
            payload={"quick_replies": get_quick_replies(request.user)},
        )

    return JsonResponse(
        {
            "session_id": chat_session.id,
            "messages": [_serialize_message(message) for message in chat_session.messages.all()],
            "quick_replies": get_quick_replies(request.user),
        }
    )


@require_POST
def send_message(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required"}, status=400)

    session_id = data.get("session_id")
    chat_session = _get_chat_session(request, session_id=session_id)

    user_message = ChatMessage.objects.create(
        session=chat_session,
        role="user",
        content=message,
        intent="user_message",
    )

    response = handle_chat_message(request.user, chat_session, message)
    bot_message = ChatMessage.objects.create(
        session=chat_session,
        role="bot",
        content=response["reply"],
        intent=response.get("intent", ""),
        payload={
            "products": response.get("products", []),
            "quick_replies": response.get("quick_replies", []),
            "meta": response.get("meta", {}),
        },
    )

    return JsonResponse(
        {
            "session_id": chat_session.id,
            "user_message": _serialize_message(user_message),
            "bot_message": _serialize_message(bot_message),
        }
    )


@require_GET
def history(request):
    session_id = request.GET.get("session_id")
    chat_session = _get_chat_session(request, session_id=session_id)
    return JsonResponse(
        {
            "session_id": chat_session.id,
            "messages": [_serialize_message(message) for message in chat_session.messages.all()],
        }
    )


@require_GET
def quick_replies(request):
    return JsonResponse({"quick_replies": get_quick_replies(request.user)})
