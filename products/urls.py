"""
URL Configuration for Products App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    BrandViewSet,
    ProductViewSet,
    ProductVariantViewSet,
    ProductImageViewSet,
    TagViewSet,
    ProductReviewViewSet
)

app_name = 'products'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'variants', ProductVariantViewSet, basename='variant')
router.register(r'images', ProductImageViewSet, basename='image')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'reviews', ProductReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]

