from django.conf import settings

from core.cache_utils import get_cached_header_context


def notifications(request):
    """
    Context processor to make notifications available in all templates.
    """
    context = get_cached_header_context(request.user)
    context["chatbot_widget_enabled"] = getattr(
        settings, "CHATBOT_WIDGET_ENABLED", False
    )
    return context

