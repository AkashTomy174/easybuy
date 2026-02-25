# views.py
from django.shortcuts import render,redirect
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from django.http import HttpResponse
from .models import SellerProfile,Product
from easybuy.core.models import Category

User = get_user_model()

def selleregi(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        store_name = request.POST.get("store_name")
        gst_number = request.POST.get("gst_number")
        pan_number = request.POST.get("pan_number")
        bank_account_number = request.POST.get("bank_account_number")
        ifsc_code = request.POST.get("ifsc_code")
        business_address = request.POST.get("business_address")
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                role="SELLER",
                is_active=True
            )
            SellerProfile.objects.create(
                user=user,
                store_name=store_name,
                store_slug=slugify(store_name),
                gst_number=gst_number,
                pan_number=pan_number,
                bank_account_number=bank_account_number,
                ifsc_code=ifsc_code,
                business_address=business_address,
            )
        return HttpResponse('waiting for approval')
    return render(request, "sellerregistration.html")


def product_list(request):
    products=Product.objects.all()
    return render(request,'all_product.html',{'products':products})
