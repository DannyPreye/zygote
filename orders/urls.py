"""
URL Configuration for Orders App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, ShippingZoneViewSet, ShippingMethodViewSet

app_name = 'orders'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'shipping-zones', ShippingZoneViewSet, basename='shipping-zone')
router.register(r'shipping-methods', ShippingMethodViewSet, basename='shipping-method')

urlpatterns = [
    path('', include(router.urls)),
]

