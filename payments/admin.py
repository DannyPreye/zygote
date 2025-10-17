from django.contrib import admin
from .models import Payment, Refund

# Register your models here.
admin.site.register([Payment, Refund])
