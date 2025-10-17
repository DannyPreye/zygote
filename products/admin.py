from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, Tag, ProductReview, ProductVariant
# Register your models here.
admin.site.register([Category, Brand, Product, ProductImage, Tag, ProductReview, ProductVariant])
