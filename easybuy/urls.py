from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import all_login

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

