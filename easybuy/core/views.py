from django.shortcuts import render, redirect

from django.contrib.auth import authenticate, login,logout
from .models import Category,User,Address
from django.http import HttpResponse
from easybuy.seller.models import SellerProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from easybuy.seller.models import Product,ProductVariant, ProductImage
from .forms import CustomerRegisterForm
from django.core.paginator import Paginator

# Create your views here.


def all_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        # print(password)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # print('user')
            login(request, user)
            role = user.role
            if role == "CUSTOMER":
                return redirect("home")
            elif role == "ADMIN":
                user=request.user
                sellers=User.objects.filter(role="SELLER").count()
                users=User.objects.filter(role="CUSTOMER").count()
                return render(request,'admin_dashboard.html',{"sellers": sellers,'users': users})
            elif role == "SELLER":
                user=request.user
                data1 = SellerProfile.objects.get(user=user)
                return render(request, "dashboard.html", {"data1": data1,'user': user})
        else:
            return render(
                request, "login.html", {"error": "Invalid username or password"}
            )
    return render(request, "login.html")

def add_category(request):
    if request.method == "POST":
        Category.objects.create(
            name=request.POST.get("name"),
            slug=request.POST.get("slug"),
            image_url=request.FILES.get("image_url"),
            description=request.POST.get("des"),
        )
        categories = Category.objects.all()
        return render(request, "display_category.html", {"categories": categories})
    return render(request, "add_category.html")


# def add_sub_category(request):
    # if request.method=="POST":
    #     data=Category.objects.all()
    #     SubCategory.objects.create(
    #         category=data,
    #         name=request.POST.get('name'),
    #         slug=request.POST.get('slug')
    #     )

def category_list(request):
    categories = Category.objects.all()
    return render(request, "display_category.html", {"categories": categories})

def seller_veri(request):
    unverified = SellerProfile.objects.filter(
        is_verified=False
    ).select_related('user')
    return render(request,'seller_veri.html',{'unverified':unverified})

def detailed_view(request,id):
    details=SellerProfile.objects.select_related('user').get(pk=id)
    return render(request,'details_view.html',{'details':details})

@login_required#user profile update
def profile_settings(request):
    if request.method == "POST":
        user = request.user
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

    return render(request, "core/profile.html")

def all_products(request):#view all product
    product_images = ProductImage.objects.filter(is_primary=True).select_related('variant__product')
    paginator = Paginator(product_images, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "core/all_products.html", {"page_obj": page_obj})

def home_view(request):# load home of user#
    categories = Category.objects.filter(is_active=True)
    product_images = ProductImage.objects.filter(is_primary=True).select_related('variant__product')
    return render(request, "core/home.html", {"categories": categories,"product_images": product_images })

def logout_view(request):
    logout(request)
    return redirect("categories")

def home_view(request):
    categories = Category.objects.filter(is_active=True)
    product_images = ProductImage.objects.filter(is_primary=True).select_related('variant__product')
    return render(request, "core/home.html", {"categories": categories,"product_images": product_images })
def register_view(request):
    if request.method == "POST":
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "CUSTOMER"
            user.save()
            login(request, user)
            return redirect("home")
    else:
        form = CustomerRegisterForm()
    return render(request, "core/register.html", {"form": form})


def cat_dis(request):
    category=Category.objects.order_by('-id')[:10]
    return render(request,'home.html'{'category':category})

def pro_dis(request):
    product=