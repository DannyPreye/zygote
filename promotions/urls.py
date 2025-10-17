"""
URL Configuration for Promotions App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromotionViewSet, CouponViewSet, PromotionStatsView

app_name = 'promotions'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = [
    # Statistics endpoint
    path('statistics/', PromotionStatsView.as_view(), name='statistics'),

    # Router URLs
    path('', include(router.urls)),
]

