from django.urls import path
from . import views
from easybuy.seller.models import Product
from easybuy.core.views import all_products

urlpatterns = [
    path("new_arrivals/", views.new_arrival, name="new_arrivals_user"),
    path("products/<int:id>/", views.product_detail, name="product_detail_by_id"),
    path(
        "category/<int:id>/",
        views.category_products,
        name="category_products_by_id_user",
    ),
    path(
        "subcategory/<int:id>/",
        views.subcategory_products,
        name="subcategory_products_by_id_user",
    ),
    path(
        "category/<slug:slug>/", views.category_products, name="category_products_user"
    ),
    path(
        "subcategory/<slug:slug>/",
        views.subcategory_products,
        name="subcategory_products_user",
    ),
    path("products/<slug:slug>/", views.product_detail, name="product_detail_user"),
    path("addtocart/<int:id>/", views.addtocart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path(
        "cart/update/<int:item_id>/",
        views.update_cart_quantity,
        name="update_cart_quantity",
    ),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("filter/", views.filtering, name="filtering"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.display_order, name="user_orders"),
    path("orders/cancel/<int:order_id>/", views.order_cancel, name="order_cancel"),
    path("buy_now/<int:variant_id>/", views.buy_now, name="buy_now"),
]
