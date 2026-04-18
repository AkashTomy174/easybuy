from django.urls import path
from . import views
from user.views import (
    home_view,
    all_categories,
    new_arrival,
    category_products,
    subcategory_products,
    product_detail,
    addtocart,
    filtering,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", views.all_login, name="all_login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("password/forgot/", views.forgot_password_view, name="forgot_password"),
    path(
        "password/reset/<uidb64>/<token>/",
        views.reset_password_view,
        name="reset_password",
    ),
    path("password/change/", views.change_password_view, name="change_password"),
    path("all-categories/", all_categories, name="all_categories"),
    path("new-arrivals/", new_arrival, name="new_arrivals"),
    path("category/<int:id>/", category_products, name="category_products_by_id"),
    path("subcategory/<int:id>/", subcategory_products, name="subcategory_products_by_id"),
    path("product/<int:id>/", product_detail, name="product_detail_by_id"),
    path("category/<slug:slug>/", category_products, name="category_products"),
    path("subcategory/<slug:slug>/", subcategory_products, name="subcategory_products"),
    path("product/<slug:slug>/", product_detail, name="product_detail"),
    path("addtocart/<int:id>/", addtocart, name="addtocart"),
    path("filter/", filtering, name="filtering"),
    path("stock-notify/<int:variant_id>/", views.toggle_stock_notification, name="toggle_stock_notify"),
    path("contact/", views.contact_view, name="contact"),
    path("returns/", views.returns_view, name="returns"),
    path("track-order/", views.track_order_view, name="track_order"),
    path("discover/", views.discover_view, name="discover"),
    path("health/", views.health_check, name="health_check"),
]
