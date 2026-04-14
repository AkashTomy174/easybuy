from core.cache_utils import get_cached_header_context


def notifications(request):
    """
    Context processor to make notifications available in all templates.
    """
    return get_cached_header_context(request.user)

