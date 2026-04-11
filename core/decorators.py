from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.shortcuts import redirect




def role_required(allowed_roles=[]):
    def decorators(view_func):
        @wraps(view_func)
        def wrap(request, *args, **kwargs):
            if not request.user.is_authenticated:
                

                return redirect_to_login(request.get_full_path())
            if request.user.role not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrap

    return decorators


def approved_seller_required(view_func):
    @wraps(view_func)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.role != "SELLER":
            raise PermissionDenied

        seller_profile = getattr(request.user, "seller_profile", None)
        if seller_profile is None:
            messages.error(request, "Complete your seller registration to access the seller portal.")
            return redirect("seller_register")

        if seller_profile.status != "APPROVED":
            return redirect("seller_waiting")

        return view_func(request, *args, **kwargs)

    return wrap
