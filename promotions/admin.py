from django.contrib import admin
from .models import Promotion, Coupon, CouponUsage
# Register your models here.
admin.site.register([Promotion, Coupon, CouponUsage])
