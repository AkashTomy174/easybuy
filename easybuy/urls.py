from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from core.views import all_login

handler403 = "core.views.custom_permission_denied_view"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("seller/", include("seller.urls")),
    path("easy_admin/", include("easybuy_admin.urls")),
    path("user/", include("user.urls")),
    path("chatbot/", include("chatbot.urls")),
    path("login/", all_login, name="login"),
    path("", include("core.urls")),
]

if settings.DEBUG or getattr(settings, "RUNNING_DEVELOPMENT_SERVER", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=str(settings.MEDIA_ROOT))
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": str(settings.MEDIA_ROOT)},
        )
    ]
