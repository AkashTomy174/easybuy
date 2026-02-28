from django.urls import path
from . import views
from easybuy.core.views import logout_view

urlpatterns = [
    path("register/", views.seller_regi, name="seller_register"),
    path("registration/success/",views.seller_regi_success,name="seller_registration_success",),
    path("inventory/", views.seller_inventory, name="seller_products_list"),
    path("sellerdashboard/", views.seller_dashboard, name="sellerdashboard"),
    path('logout/', logout_view, name='logout'),
]
