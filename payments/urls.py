"""
URL Configuration for Payments App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, RefundViewSet, PaymentWebhookView

app_name = 'payments'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')

urlpatterns = [
    # Webhook endpoints (must be before router)
    path('webhooks/<str:gateway>/', PaymentWebhookView.as_view(), name='webhook'),

    # Router URLs
    path('', include(router.urls)),
]

