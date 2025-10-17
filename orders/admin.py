from django.contrib import admin
from .models import Order, OrderItem, ShippingZone, ShippingMethod
# Register your models here.
admin.site.register([Order, OrderItem, ShippingZone, ShippingMethod])
