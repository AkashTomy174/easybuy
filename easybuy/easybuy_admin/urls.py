from django.urls import path
from . import views
from easybuy.core.views import all_categories, logout_view


urlpatterns = [
    path("home/seller_veri/", views.seller_veri, name="seller_veri"),
    path("home/approve_seller/<int:id>/", views.approve_seller, name="approve_seller"),
    path("home/reject_seller/<int:id>/", views.reject_seller, name="reject_seller"),
    path("home/seller_details/<int:id>/", views.detailed_view, name="seller_details"),
    path("categories/", all_categories, name="admin_all_categories"),
    path("add_category/", views.add_category, name="add_category"),
    path("users/", views.all_users, name="all_users"),
    path("sellers/", views.all_sellers, name="all_sellers"),
    path("logout/", logout_view, name="logout"),
]
