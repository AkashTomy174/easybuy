from django.shortcuts import render

# Create your views here.
# class Product(models.Model):
#     seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="products")
#     subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="products")
#     name = models.CharField(max_length=255)
#     slug = models.SlugField()
#     description = models.TextField()
#     brand = models.CharField(max_length=100)
#     model_number = models.CharField(max_length=100)
#     is_cancellable = models.BooleanField(default=True)
#     is_returnable = models.BooleanField(default=True)
#     return_days = models.IntegerField(default=7)
#     approval_status = models.CharField(max_length=20, default='PENDING')
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
