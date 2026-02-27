from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('home/', views.home_view, name='home'),
    path('products/', views.all_new_products, name='all_new_products'),
    path('profile/', views.profile_settings, name='profile_settings'),
    path('profile/addresses/', views.manage_addresses, name='manage_addresses'),
    path('profile/addresses/add/', views.user_address, name='user_address'),
    path('profile/addresses/delete/<int:id>/', views.delete_address, name='delete_address'),
    path('profile/addresses/edit/<int:id>/', views.edit_address, name='edit_address'),
    path('category/', views.all_categories, name='all_categories'),
    path('categoryproduct/<int:id>/',views.category_products,name='category_products'),
    path('category/<int:id>/', views.category_products, name='category_products'),
    path('subcategory/<int:id>/', views.subcategory_products, name='subcategory_products'),


]
