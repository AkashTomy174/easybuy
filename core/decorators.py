from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render

from core.models import User
from seller.models import SellerProfile

GENERIC_PERMISSION_DENIED_MESSAGE = (
    "You do not have permission to access this resource."
)

def _expects_json_response(request):
    accept_header = (request.headers.get("Accept") or "").lower()
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in accept_header
    )

def permission_denied_response(
    request,
    *,
    message=GENERIC_PERMISSION_DENIED_MESSAGE,
    status=403,
):
    payload = {"success": False, "message": message}
    if _expects_json_response(request):
        return JsonResponse(payload, status=status)
    return render(request, "403.html", payload, status=status)


def role_required(allowed_roles=None, *, permission=None):
    normalized_roles = tuple(allowed_roles or ())

    def decorators(view_func):
        @login_required
        @wraps(view_func)
        def wrap(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if normalized_roles and not request.user.has_role(*normalized_roles):
                return permission_denied_response(request)
            if permission and not request.user.has_permission(permission):
                return permission_denied_response(request)
            return view_func(request, *args, **kwargs)

        return wrap

    return decorators


def approved_seller_required(view_func):
    @login_required
    @wraps(view_func)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if not request.user.has_role(User.ROLE_SELLER):
            return permission_denied_response(request)

        seller_profile = getattr(request.user, "seller_profile", None)
        if seller_profile is None:
            return permission_denied_response(request)

        if seller_profile.status != SellerProfile.STATUS_APPROVED:
            return permission_denied_response(request)

        if not request.user.has_permission("seller:access"):
            return permission_denied_response(request)

        return view_func(request, *args, **kwargs)

    return wrap
