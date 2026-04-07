from django.urls import path
from . import views
from user.views import all_categories
from core.views import logout_view

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("home/seller_veri/", views.seller_veri, name="seller_veri"),
    path("home/approve_seller/<int:id>/", views.approve_seller, name="approve_seller"),
    path("home/reject_seller/<int:id>/", views.reject_seller, name="reject_seller"),
    path("home/seller_details/<int:id>/", views.detailed_view, name="seller_details"),
    path("categories/", views.admin_all_categories, name="admin_all_categories"),
    path("add_category/", views.add_category, name="add_category"),
    path("add_subcategory/", views.add_subcategory, name="add_subcategory"),
    path("banners/", views.banner_list, name="admin_banner_list"),
    path("banners/add/", views.add_banner, name="add_banner"),
    path("banners/toggle/<int:id>/", views.toggle_banner_status, name="toggle_banner_status"),
    path("users/", views.all_users, name="all_users"),
    path("sellers/", views.all_sellers, name="all_sellers"),
    path("logout/", logout_view, name="logout"),
    path("approve_products/", views.approve_product, name="approve_products"),
    path(
        "approve_product/<int:id>/",
        views.approve_single_product,
        name="approve_single_product",
    ),
    path(
        "reject_product/<int:id>/",
        views.reject_single_product,
        name="reject_single_product",
    ),
    path("rejectedseller/", views.rejected_sellers, name="rejectedsellers"),
    path("rejectedproduct/", views.rejected_products, name="rejectedproducts"),
    path('admin/category/toggle/<int:id>/', views.toggle_category_status, name='toggle_category_status'),
    path('admin/subcategory/toggle/<int:id>/', views.toggle_subcategory_status, name='toggle_subcategory_status'),
]

