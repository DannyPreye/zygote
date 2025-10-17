from django.contrib import admin
from .models import Warehouse, InventoryItem, StockMovement, StockAlert, Supplier, PurchaseOrder, PurchaseOrderItem

# Register your models here.
admin.site.register([Warehouse, InventoryItem, StockMovement, StockAlert, Supplier, PurchaseOrder, PurchaseOrderItem])
