from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomerRegisterForm
from .models import Category,Address,SubCategory
from easybuy.seller.models import Product,ProductVariant, ProductImage
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
User = get_user_model()

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if not username or not email or not password1:
            messages.error(request, "All fields are required.")
            return redirect("register")
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,)
        user.role = "CUSTOMER"
        user.save()
        login(request, user)
        return redirect("home")

    return render(request, "core/register.html")

def login_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)   
        if user is not None:
            login(request, user)
            return redirect("home") 
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, "core/login.html")

def logout_view(request):
    logout(request)
    return redirect("home")

def home_view(request):
    categories = Category.objects.filter(is_active=True)[:4]
    latest_products = Product.objects.all().prefetch_related('variants__images').order_by('-id')[:4]
    return render(request, "core/home.html", {"categories": categories, "latest_products": latest_products})

def all_new_products(request):
    new_arrivals = ProductImage.objects.filter(
        is_primary=True, variant__product__is_active=True ).select_related('variant__product').order_by('-id')
    paginator = Paginator(new_arrivals, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "core/all_new_products.html", {"page_obj": page_obj})


@login_required
def profile_settings(request):
    user = request.user
    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first()
  
    if request.method == "POST":
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.dob = request.POST.get('dob') if request.POST.get('dob') else None
        user.gender = request.POST.get('gender')
        if request.FILES.get('profile_image'):
            user.profile_image = request.FILES.get('profile_image')  
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('profile_settings')
    return render(request, "core/profile.html", {'addresses': addresses,'default_address': default_address,'user':user})

@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-id')
    return render(request, "core/addresses.html", {'addresses': addresses})

@login_required
def user_address(request):
    if request.method=="POST":
        full_name=request.POST.get('fullname')   
        phone = request.POST.get('phone')
        pincode = request.POST.get('pincode')
        locality = request.POST.get('locality')
        house = request.POST.get('house_info')
        city = request.POST.get('city')
        state = request.POST.get('state')
        addr_type = request.POST.get('address_type')
        is_default = request.POST.get('is_default')== "on"
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
        Address.objects.create(user=request.user,
        full_name=full_name,
        phone_number=phone,
        pincode=pincode,
        locality=locality,
        house_info=house,
        city=city,
        state=state,
        address_type=addr_type,
        is_default=is_default)
        return redirect('manage_addresses')
                
@login_required
def delete_address(request, id):
    address = Address.objects.get(id=id, user=request.user)
    address.delete()
    return redirect('manage_addresses')

@login_required
def edit_address(request,id):
    address=Address.objects.get(id=id,user=request.user)
    if request.method=="POST":
        address.full_name = request.POST.get('fullname')
        address.phone_number = request.POST.get('phone')
        address.house_info = request.POST.get('house_info')
        address.locality = request.POST.get('locality')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.pincode = request.POST.get('pincode')
        address.address_type = request.POST.get('address_type')
        is_default = request.POST.get('is_default') == "on"
        if is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
            address.is_default = True
        else:
            address.is_default = False
        address.save()
    return redirect('manage_addresses')


def all_categories(request):
    all_categories = Category.objects.filter(is_active=True).order_by('id')
    return render(request, "core/all_categories.html", {"all_categories": all_categories })


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