from django.urls import path
from . import views
from easybuy.core.views import logout_view

urlpatterns = [
    path("dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("register/", views.seller_regi, name="seller_register"),
    path(
        "registration/success/",
        views.seller_regi_success,
        name="seller_registration_success",
    ),
    path("inventory/", views.seller_inventory, name="seller_products_list"),
    path("sellerdashboard/", views.seller_dashboard, name="sellerdashboard"),
    path("logout/", logout_view, name="logout"),
    path("add-product/", views.add_product, name="add_product"),
    path("add_stock/", views.add_stock, name="add_stock"),
    path("deactivate/<int:id>/", views.deactivate, name="deactivate"),
    path("orders/", views.seller_order, name="seller_orders"),
    path("status/<int:id>/", views.status, name="status"),
    path("reviews/", views.seller_reviews, name="seller_reviews"),
    path("reviews/reply/<int:review_id>/", views.reply_review, name="reply_review"),
]
