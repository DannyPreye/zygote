"""
URL Configuration for Recommendations App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductInteractionViewSet,
    TrackInteractionView,
    GetRecommendationsView,
    SimilarProductsView,
    TrendingProductsView,
    PersonalizedRecommendationsView,
    FrequentlyBoughtTogetherView,
    RecentlyViewedView,
    CustomerBehaviorView,
    ProductPopularityView,
    RecommendationPerformanceView,
)

app_name = 'recommendations'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'interactions', ProductInteractionViewSet, basename='interaction')

urlpatterns = [
    # Tracking
    path('track/', TrackInteractionView.as_view(), name='track'),

    # Recommendations
    path('get-recommendations/', GetRecommendationsView.as_view(), name='get-recommendations'),
    path('similar-products/', SimilarProductsView.as_view(), name='similar-products'),
    path('trending/', TrendingProductsView.as_view(), name='trending'),
    path('personalized/', PersonalizedRecommendationsView.as_view(), name='personalized'),
    path('frequently-bought-together/', FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('recently-viewed/', RecentlyViewedView.as_view(), name='recently-viewed'),

    # Analytics (Admin only)
    path('analytics/customer-behavior/', CustomerBehaviorView.as_view(), name='customer-behavior'),
    path('analytics/product-popularity/', ProductPopularityView.as_view(), name='product-popularity'),
    path('analytics/performance/', RecommendationPerformanceView.as_view(), name='performance'),

    # Router URLs
    path('', include(router.urls)),
]

