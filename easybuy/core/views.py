from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import Category,User
from django.http import HttpResponse
from easybuy.seller.models import SellerProfile

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
#     if request.method=="POST":
#         data=Category.objects.all()
#         SubCategory.objects.create(
#             category=data,
#             name=request.POST.get('name'),
#             slug=request.POST.get('slug')
#         )

def category_list(request):
    categories = Category.objects.all()
    return render(request, "display_category.html", {"categories": categories})

def seller_veri(request):
    unverified = SellerProfile.objects.filter(
        is_verified=False
    ).select_related('user')