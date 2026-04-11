from django.urls import path
from . import views
from core.views import logout_view

urlpatterns = [
    path("dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("access/", views.seller_waiting, name="seller_waiting"),
    path("register/", views.seller_regi, name="seller_register"),
    path(
        "registration/success/",
        views.seller_regi_success,
        name="seller_registration_success",
    ),
    path("inventory/", views.seller_inventory, name="seller_products_list"),
    path("promotions/", views.seller_promo_codes, name="seller_promo_codes"),
    path("promotions/toggle/<int:coupon_id>/", views.toggle_seller_promo_code, name="toggle_seller_promo_code"),
    path("sellerdashboard/", views.seller_dashboard, name="sellerdashboard"),
    path("logout/", logout_view, name="logout"),
    path("add-product/", views.add_product, name="add_product"),
    
    path('add_variant/<int:product_id>/', views.add_variant, name='add_variant'),
    path("select-product-variant/", views.select_product_for_variant, name="select_product_for_variant"), 
    path("add_stock/", views.add_stock, name="add_stock"),
    path("deactivate/<int:id>/", views.deactivate, name="deactivate"),
    path("orders/", views.seller_order, name="seller_orders"),
    path("status/<int:id>/", views.status, name="status"),
    path("reviews/", views.seller_reviews, name="seller_reviews"),
    path("reviews/reply/<int:review_id>/", views.reply_review, name="reply_review"),
    path("returns/", views.seller_returns, name="seller_returns"),
    path("returns/process/<int:id>/", views.process_return, name="process_return"),
]

