"""
URL Configuration for Customers App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet,
    AddressViewSet,
    CustomerGroupViewSet,
    CustomerRegistrationView
)

app_name = 'customers'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'groups', CustomerGroupViewSet, basename='group')

urlpatterns = [
    # Registration endpoint (public)
    path('register/', CustomerRegistrationView.as_view(), name='register'),

    # Router URLs
    path('', include(router.urls)),
]

