from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login




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
