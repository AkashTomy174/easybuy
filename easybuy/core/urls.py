from django.urls import path
from . import views
from easybuy.user.views import  new_arrival
urlpatterns = [

    path('', views.home_view, name='home'),
    path('login/', views.all_login, name='all_login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_settings, name='profile_settings'),
    path('products/', views.all_products, name='all_products'),
   
    path('all-categories/', views.all_categories, name='all_categories'),
    path('new-arrivals/', new_arrival, name='new_arrivals'),
    path('profile/addresses/', views.manage_addresses, name='manage_addresses'),
    path('profile/addresses/add/', views.user_address, name='user_address'),
    path('profile/addresses/delete/<int:id>/', views.delete_address, name='delete_address'),
    path('profile/addresses/edit/<int:id>/', views.edit_address, name='edit_address'),

]

