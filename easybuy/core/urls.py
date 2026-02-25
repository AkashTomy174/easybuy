from django.urls import path
from . import views


urlpatterns=[
    path('add_categories', views.add_category, name='add_category'),
    path('home',views.all_login,name='all_login'),
    path('category_list',views.category_list,name='category_list'),
    
]


