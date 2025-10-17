from django.contrib import admin
from .models import Customer, CustomerGroup, Address

# Register your models here.
admin.site.register([Customer, CustomerGroup, Address])
