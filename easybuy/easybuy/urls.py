from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from easybuy.core.views import all_login

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("easybuy.core.urls")),
    path("seller/", include("easybuy.seller.urls")),
    path("easy_admin/", include("easybuy.easybuy_admin.urls")),
    path("user/", include("easybuy.user.urls")),
    path("login/", all_login, name="login"),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
