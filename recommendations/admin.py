from django.contrib import admin
from .models import ProductInteraction, RecommendationLog

# Register your models here.
admin.site.register([ProductInteraction, RecommendationLog])
