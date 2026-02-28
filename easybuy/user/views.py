from django.shortcuts import render

from easybuy.core.models import SubCategory,Category
from easybuy.seller.models import Product



def new_arrival(request):
    products = Product.objects.filter(
        is_active=True,
        approval_status='APPROVED'
    ).order_by('-created_at')[:8]
    return render(request, 'user/new_arrivals.html', {'products': products})
def category_products(request, id):
    categories = Category.objects.get(id=id)
    subcategory = SubCategory.objects.filter(category=categories)
    product = Product.objects.filter(subcategory__category=categories, is_active=True).prefetch_related('variants__images')
    return render(request, 'core/category_products.html', {
        'categories': categories,
        'subcategory': subcategory,
        'product': product,
        'active_sub': None})

def subcategory_products(request, id):
    current_sub = SubCategory.objects.get(id=id)
    categories = current_sub.category
    subcategory = SubCategory.objects.filter(category=categories)
    product = Product.objects.filter(subcategory=current_sub, is_active=True).prefetch_related('variants__images')
    
    return render(request, 'core/category_products.html', {
        'categories': categories,
        'subcategory': subcategory,
        'product': product,
        'active_sub': id 
    }) 
def product_detail(request, id):
    product = Product.objects.filter(id=id, is_active=True).prefetch_related('variants__images').first()
    if not product:
        return render(request, 'core/product_detail.html', {'error': 'Product not found'})
    return render(request, 'core/product_detail.html', {'product': product})


