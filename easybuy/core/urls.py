from django.urls import path
from . import views
from easybuy.user.views import new_arrival
from easybuy.user.views import (
    category_products,
    subcategory_products,
    product_detail,
    addtocart,
    filtering,
)

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", views.all_login, name="all_login"),
    path("admin_dashboard/",views.admin_dashboard,name="admin_dashboard"),
    path("seller_dashboard/",views.seller_dashboard,name="seller_dashboard"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_settings, name="profile_settings"),
    path("products/", views.all_products, name="all_products"),
    path("all-categories/", views.all_categories, name="all_categories"),
    path("new-arrivals/", new_arrival, name="new_arrivals"),
    path("profile/addresses/", views.manage_addresses, name="manage_addresses"),
    path("profile/addresses/add/", views.user_address, name="user_address"),
    path("profile/addresses/delete/<int:id>/",views.delete_address,name="delete_address",),
    path("profile/addresses/edit/<int:id>/", views.edit_address, name="edit_address"),
    path("category/<int:id>/", category_products, name="category_products_by_id"),
    path("subcategory/<int:id>/", subcategory_products, name="subcategory_products_by_id"),
    path("product/<int:id>/", product_detail, name="product_detail_by_id"),
    path("category/<slug:slug>/", category_products, name="category_products"),
    path("subcategory/<slug:slug>/", subcategory_products, name="subcategory_products"),
    path("product/<slug:slug>/", product_detail, name="product_detail"),
    path("addtocart/<int:id>/", addtocart, name="addtocart"),
    path("filter/", filtering, name="filtering"),
]
