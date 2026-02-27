from functools import wraps
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles=[]):
    def decorators(view_func):
        @wraps(view_func)
        def wrap(request,*args,**kwargs):
            if request.user.is_authenticated and request.user.role in allowed_roles:
                return view_func(request,*args,**kwargs)
            raise PermissionDenied
        return wrap
    return decorators