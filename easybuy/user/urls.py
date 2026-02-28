from django.urls import path
from . import views
from easybuy.seller.models import Product
from easybuy.core.views import all_products

urlpatterns = [
    path("all_products/", all_products, name="all_products"),
    path("new_arrivals/", views.new_arrival, name="new_arrivals"),
    path("category/<int:id>/", views.category_products, name="category_products"),
    path("subcategory/<int:id>/", views.subcategory_products, name="subcategory_products"),
    path("products/<int:id>/", views.product_detail, name="product_detail"),
]
