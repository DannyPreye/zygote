"""
URL Configuration for Inventory App
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WarehouseViewSet,
    InventoryItemViewSet,
    StockMovementViewSet,
    StockAlertViewSet,
    SupplierViewSet,
    PurchaseOrderViewSet,
    InventoryStatsViewSet
)

app_name = 'inventory'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'items', InventoryItemViewSet, basename='item')
router.register(r'movements', StockMovementViewSet, basename='movement')
router.register(r'alerts', StockAlertViewSet, basename='alert')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'stats', InventoryStatsViewSet, basename='stats')

urlpatterns = [
    path('', include(router.urls)),
]

