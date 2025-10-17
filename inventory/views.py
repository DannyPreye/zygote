"""
Inventory Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q, Sum, F, Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import (
    Warehouse,
    InventoryItem,
    StockMovement,
    StockAlert,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)
from .serializers import (
    WarehouseSerializer,
    WarehouseListSerializer,
    InventoryItemSerializer,
    InventoryItemUpdateSerializer,
    StockMovementSerializer,
    StockMovementCreateSerializer,
    StockAlertSerializer,
    SupplierSerializer,
    SupplierListSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderItemSerializer,
    InventoryStatsSerializer,
)
from .filters import InventoryItemFilter, StockMovementFilter, PurchaseOrderFilter
from api.permissions import CanManageInventory


# ============================================================================
# WAREHOUSE VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all warehouses",
        description="Retrieve a list of all warehouses with filtering",
        parameters=[
            OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, description='Filter active warehouses'),
            OpenApiParameter(name='can_ship', type=OpenApiTypes.BOOL, description='Filter warehouses that can ship'),
            OpenApiParameter(name='country', type=OpenApiTypes.STR, description='Filter by country'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get warehouse details",
        description="Retrieve detailed information about a specific warehouse",
        tags=['Inventory'],
    ),
    create=extend_schema(
        summary="Create new warehouse",
        description="Create a new warehouse location",
        tags=['Inventory'],
    ),
    update=extend_schema(
        summary="Update warehouse",
        description="Update warehouse information",
        tags=['Inventory'],
    ),
    destroy=extend_schema(
        summary="Delete warehouse",
        description="Delete a warehouse (if no inventory exists)",
        tags=['Inventory'],
    ),
)
class WarehouseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing warehouses.

    Warehouses are physical locations where inventory is stored.
    """
    queryset = Warehouse.objects.all()
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'can_ship', 'can_receive', 'country', 'state']
    search_fields = ['name', 'code', 'city', 'address']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return WarehouseListSerializer
        return WarehouseSerializer

    @extend_schema(
        summary="Get warehouse inventory",
        description="Get all inventory items in this warehouse",
        parameters=[
            OpenApiParameter(name='low_stock', type=OpenApiTypes.BOOL, description='Filter low stock items'),
        ],
        tags=['Inventory'],
    )
    @action(detail=True, methods=['get'])
    def inventory(self, request, pk=None):
        """Get inventory items in warehouse"""
        warehouse = self.get_object()
        items = InventoryItem.objects.filter(warehouse=warehouse, is_active=True)

        # Filter low stock items
        if request.query_params.get('low_stock') == 'true':
            items = items.filter(quantity_available__lte=F('reorder_level'))

        serializer = InventoryItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get warehouse stats",
        description="Get statistics for the warehouse",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get warehouse statistics"""
        warehouse = self.get_object()

        items = InventoryItem.objects.filter(warehouse=warehouse, is_active=True)

        stats = {
            'total_items': items.count(),
            'total_quantity': items.aggregate(total=Sum('quantity_on_hand'))['total'] or 0,
            'total_available': items.aggregate(total=Sum('quantity_available'))['total'] or 0,
            'total_reserved': items.aggregate(total=Sum('quantity_reserved'))['total'] or 0,
            'low_stock_items': items.filter(quantity_available__lte=F('reorder_level')).count(),
            'out_of_stock_items': items.filter(quantity_available=0).count(),
            'capacity_used': warehouse.current_capacity,
            'capacity_max': warehouse.max_capacity,
            'capacity_percentage': (warehouse.current_capacity / warehouse.max_capacity * 100) if warehouse.max_capacity else 0,
        }

        return Response(stats)

    @extend_schema(
        summary="Set as default warehouse",
        description="Set this warehouse as the default",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set warehouse as default"""
        warehouse = self.get_object()

        # Unset other defaults
        Warehouse.objects.all().update(is_default=False)

        # Set this as default
        warehouse.is_default = True
        warehouse.save()

        return Response({
            'message': 'Warehouse set as default',
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name
        })


# ============================================================================
# INVENTORY ITEM VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all inventory items",
        description="Retrieve inventory items with comprehensive filtering",
        parameters=[
            OpenApiParameter(name='warehouse', type=OpenApiTypes.INT, description='Filter by warehouse ID'),
            OpenApiParameter(name='product', type=OpenApiTypes.INT, description='Filter by product ID'),
            OpenApiParameter(name='low_stock', type=OpenApiTypes.BOOL, description='Filter low stock items'),
            OpenApiParameter(name='out_of_stock', type=OpenApiTypes.BOOL, description='Filter out of stock items'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get inventory item details",
        description="Retrieve detailed information about a specific inventory item",
        tags=['Inventory'],
    ),
    create=extend_schema(
        summary="Create inventory item",
        description="Add a new product to warehouse inventory",
        tags=['Inventory'],
    ),
    update=extend_schema(
        summary="Update inventory item",
        description="Update inventory item information",
        tags=['Inventory'],
    ),
    destroy=extend_schema(
        summary="Delete inventory item",
        description="Remove an item from inventory",
        tags=['Inventory'],
    ),
)
class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing inventory items.

    Tracks stock levels for products in warehouses.
    """
    queryset = InventoryItem.objects.select_related('product', 'variant', 'warehouse').filter(is_active=True)
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryItemFilter
    search_fields = ['product__name', 'product__sku', 'variant__sku']
    ordering_fields = ['quantity_available', 'quantity_on_hand', 'reorder_level', 'last_counted_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return InventoryItemUpdateSerializer
        return InventoryItemSerializer

    @extend_schema(
        summary="Adjust stock",
        description="Adjust inventory stock levels (add or remove)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'quantity': {'type': 'integer', 'example': 100},
                    'movement_type': {'type': 'string', 'enum': ['purchase', 'adjustment', 'damage', 'return'], 'example': 'purchase'},
                    'notes': {'type': 'string', 'example': 'Restocking from supplier'},
                },
                'required': ['quantity', 'movement_type']
            }
        },
        responses={200: InventoryItemSerializer},
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust inventory stock"""
        inventory_item = self.get_object()

        quantity = request.data.get('quantity')
        movement_type = request.data.get('movement_type')
        notes = request.data.get('notes', '')

        if not quantity or not movement_type:
            return Response(
                {'error': 'quantity and movement_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except ValueError:
            return Response(
                {'error': 'quantity must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create stock movement
        with transaction.atomic():
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type=movement_type,
                quantity=abs(quantity),
                notes=notes,
                user=request.user
            )

            # Update inventory
            if movement_type in ['purchase', 'return', 'adjustment'] and quantity > 0:
                inventory_item.quantity_on_hand += quantity
            elif movement_type in ['damage', 'adjustment'] and quantity < 0:
                inventory_item.quantity_on_hand += quantity  # quantity is negative

            # Recalculate available
            inventory_item.quantity_available = inventory_item.quantity_on_hand - inventory_item.quantity_reserved
            inventory_item.save()

        serializer = self.get_serializer(inventory_item)
        return Response(serializer.data)

    @extend_schema(
        summary="Reserve stock",
        description="Reserve stock for an order",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'quantity': {'type': 'integer', 'example': 5},
                    'order_id': {'type': 'integer', 'example': 123},
                },
                'required': ['quantity']
            }
        },
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """Reserve inventory for order"""
        inventory_item = self.get_object()
        quantity = request.data.get('quantity', 0)
        order_id = request.data.get('order_id')

        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if inventory_item.quantity_available < quantity:
            return Response(
                {'error': 'Insufficient stock available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            inventory_item.quantity_reserved += quantity
            inventory_item.quantity_available -= quantity
            inventory_item.save()

            # Create movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type='sale',
                quantity=quantity,
                reference_type='order',
                reference_id=order_id,
                notes=f'Reserved for order #{order_id}',
                user=request.user
            )

        return Response({
            'message': 'Stock reserved successfully',
            'quantity_reserved': quantity,
            'quantity_available': inventory_item.quantity_available
        })

    @extend_schema(
        summary="Release reserved stock",
        description="Release reserved stock (e.g., cancelled order)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'quantity': {'type': 'integer', 'example': 5},
                },
                'required': ['quantity']
            }
        },
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release reserved stock"""
        inventory_item = self.get_object()
        quantity = request.data.get('quantity', 0)

        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if inventory_item.quantity_reserved < quantity:
            return Response(
                {'error': 'Cannot release more than reserved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            inventory_item.quantity_reserved -= quantity
            inventory_item.quantity_available += quantity
            inventory_item.save()

        return Response({
            'message': 'Stock released successfully',
            'quantity_available': inventory_item.quantity_available,
            'quantity_reserved': inventory_item.quantity_reserved
        })

    @extend_schema(
        summary="Get stock history",
        description="Get stock movement history for this item",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get stock movement history"""
        inventory_item = self.get_object()
        movements = StockMovement.objects.filter(
            inventory_item=inventory_item
        ).order_by('-created_at')

        serializer = StockMovementSerializer(movements, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Check low stock",
        description="Check if item needs reordering",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['get'])
    def check_reorder(self, request, pk=None):
        """Check if item needs reordering"""
        inventory_item = self.get_object()

        needs_reorder = inventory_item.quantity_available <= inventory_item.reorder_level

        return Response({
            'needs_reorder': needs_reorder,
            'quantity_available': inventory_item.quantity_available,
            'reorder_level': inventory_item.reorder_level,
            'reorder_quantity': inventory_item.reorder_quantity,
            'suggested_order': inventory_item.reorder_quantity if needs_reorder else 0
        })


# ============================================================================
# STOCK MOVEMENT VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List stock movements",
        description="Retrieve stock movement history with filtering",
        parameters=[
            OpenApiParameter(name='inventory_item', type=OpenApiTypes.INT, description='Filter by inventory item'),
            OpenApiParameter(name='movement_type', type=OpenApiTypes.STR, description='Filter by movement type'),
            OpenApiParameter(name='warehouse', type=OpenApiTypes.INT, description='Filter by warehouse'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get movement details",
        description="Retrieve detailed information about a stock movement",
        tags=['Inventory'],
    ),
    create=extend_schema(
        summary="Create stock movement",
        description="Record a new stock movement",
        tags=['Inventory'],
    ),
)
class StockMovementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tracking stock movements.

    Records all inventory changes with audit trail.
    """
    queryset = StockMovement.objects.select_related('inventory_item', 'user').all()
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StockMovementFilter
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']
    http_method_names = ['get', 'post']  # No update/delete

    def get_serializer_class(self):
        if self.action == 'create':
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def perform_create(self, serializer):
        """Create movement and update inventory"""
        serializer.save(user=self.request.user)


# ============================================================================
# STOCK ALERT VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List stock alerts",
        description="Retrieve active stock alerts",
        parameters=[
            OpenApiParameter(name='alert_type', type=OpenApiTypes.STR, description='Filter by alert type'),
            OpenApiParameter(name='is_resolved', type=OpenApiTypes.BOOL, description='Filter by resolution status'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get alert details",
        description="Retrieve detailed information about a stock alert",
        tags=['Inventory'],
    ),
)
class StockAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing stock alerts.

    Alerts are automatically generated for low stock and out of stock items.
    """
    queryset = StockAlert.objects.select_related('inventory_item').all()
    serializer_class = StockAlertSerializer
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'is_resolved', 'inventory_item__warehouse']
    ordering_fields = ['created_at', 'resolved_at']
    ordering = ['-created_at']

    @extend_schema(
        summary="Resolve alert",
        description="Mark a stock alert as resolved",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve stock alert"""
        alert = self.get_object()

        if alert.is_resolved:
            return Response(
                {'message': 'Alert already resolved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()

        return Response({
            'message': 'Alert resolved successfully',
            'alert_id': alert.id,
            'resolved_at': alert.resolved_at
        })

    @extend_schema(
        summary="Get unresolved alerts",
        description="Get all unresolved stock alerts",
        tags=['Inventory'],
    )
    @action(detail=False, methods=['get'])
    def unresolved(self, request):
        """Get unresolved alerts"""
        alerts = self.queryset.filter(is_resolved=False)
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)


# ============================================================================
# SUPPLIER VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all suppliers",
        description="Retrieve a list of all suppliers",
        parameters=[
            OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, description='Filter active suppliers'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get supplier details",
        description="Retrieve detailed information about a specific supplier",
        tags=['Inventory'],
    ),
    create=extend_schema(
        summary="Create new supplier",
        description="Add a new supplier to the system",
        tags=['Inventory'],
    ),
    update=extend_schema(
        summary="Update supplier",
        description="Update supplier information",
        tags=['Inventory'],
    ),
    destroy=extend_schema(
        summary="Delete supplier",
        description="Delete a supplier",
        tags=['Inventory'],
    ),
)
class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing suppliers.

    Suppliers provide inventory through purchase orders.
    """
    queryset = Supplier.objects.all()
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'country']
    search_fields = ['name', 'contact_person', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return SupplierListSerializer
        return SupplierSerializer

    @extend_schema(
        summary="Get supplier purchase orders",
        description="Get all purchase orders from this supplier",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['get'])
    def purchase_orders(self, request, pk=None):
        """Get supplier's purchase orders"""
        supplier = self.get_object()
        orders = PurchaseOrder.objects.filter(supplier=supplier).order_by('-created_at')

        serializer = PurchaseOrderListSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


# ============================================================================
# PURCHASE ORDER VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List purchase orders",
        description="Retrieve all purchase orders with filtering",
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, description='Filter by status'),
            OpenApiParameter(name='supplier', type=OpenApiTypes.INT, description='Filter by supplier'),
        ],
        tags=['Inventory'],
    ),
    retrieve=extend_schema(
        summary="Get purchase order details",
        description="Retrieve detailed information about a purchase order",
        tags=['Inventory'],
    ),
    create=extend_schema(
        summary="Create purchase order",
        description="Create a new purchase order to a supplier",
        tags=['Inventory'],
    ),
    update=extend_schema(
        summary="Update purchase order",
        description="Update purchase order details",
        tags=['Inventory'],
    ),
)
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing purchase orders.

    Purchase orders are used to restock inventory from suppliers.
    """
    queryset = PurchaseOrder.objects.select_related('supplier', 'warehouse', 'created_by').prefetch_related('items')
    permission_classes = [CanManageInventory]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PurchaseOrderFilter
    ordering_fields = ['created_at', 'expected_delivery_date', 'total_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseOrderListSerializer
        elif self.action == 'create':
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer

    def perform_create(self, serializer):
        """Create purchase order with created_by"""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Send to supplier",
        description="Mark purchase order as sent to supplier",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send purchase order to supplier"""
        po = self.get_object()

        if po.status != 'draft':
            return Response(
                {'error': 'Only draft orders can be sent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        po.status = 'sent'
        po.save()

        return Response({
            'message': 'Purchase order sent to supplier',
            'po_number': po.po_number,
            'status': po.status
        })

    @extend_schema(
        summary="Confirm order",
        description="Mark purchase order as confirmed by supplier",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm purchase order"""
        po = self.get_object()

        if po.status != 'sent':
            return Response(
                {'error': 'Only sent orders can be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        po.status = 'confirmed'
        po.save()

        return Response({
            'message': 'Purchase order confirmed',
            'po_number': po.po_number,
            'status': po.status
        })

    @extend_schema(
        summary="Receive order",
        description="Mark purchase order as received and update inventory",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'items': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'item_id': {'type': 'integer'},
                                'quantity_received': {'type': 'integer'},
                            }
                        }
                    }
                },
                'required': ['items']
            }
        },
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Receive purchase order and update inventory"""
        po = self.get_object()

        if po.status not in ['sent', 'confirmed']:
            return Response(
                {'error': 'Order must be sent or confirmed to receive'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items_data = request.data.get('items', [])

        if not items_data:
            return Response(
                {'error': 'Items data required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            for item_data in items_data:
                item_id = item_data.get('item_id')
                qty_received = item_data.get('quantity_received', 0)

                try:
                    po_item = PurchaseOrderItem.objects.get(id=item_id, purchase_order=po)
                except PurchaseOrderItem.DoesNotExist:
                    continue

                # Update PO item
                po_item.quantity_received += qty_received
                po_item.save()

                # Update inventory
                inventory_item, created = InventoryItem.objects.get_or_create(
                    product=po_item.product,
                    variant=po_item.variant,
                    warehouse=po.warehouse,
                    defaults={
                        'quantity_on_hand': qty_received,
                        'quantity_available': qty_received
                    }
                )

                if not created:
                    inventory_item.quantity_on_hand += qty_received
                    inventory_item.quantity_available = inventory_item.quantity_on_hand - inventory_item.quantity_reserved
                    inventory_item.save()

                # Create stock movement
                StockMovement.objects.create(
                    inventory_item=inventory_item,
                    movement_type='purchase',
                    quantity=qty_received,
                    reference_type='purchase_order',
                    reference_id=po.id,
                    notes=f'Received from PO #{po.po_number}',
                    user=request.user
                )

            # Update PO status
            po.status = 'received'
            po.actual_delivery_date = timezone.now().date()
            po.save()

        return Response({
            'message': 'Purchase order received successfully',
            'po_number': po.po_number,
            'status': po.status
        })

    @extend_schema(
        summary="Cancel order",
        description="Cancel a purchase order",
        tags=['Inventory'],
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel purchase order"""
        po = self.get_object()

        if po.status == 'received':
            return Response(
                {'error': 'Cannot cancel received orders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        po.status = 'cancelled'
        po.save()

        return Response({
            'message': 'Purchase order cancelled',
            'po_number': po.po_number,
            'status': po.status
        })


# ============================================================================
# INVENTORY REPORTS & ANALYTICS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Get inventory statistics",
        description="Get comprehensive inventory analytics and reports",
        tags=['Inventory'],
    ),
)
class InventoryStatsViewSet(viewsets.ViewSet):
    """
    API endpoint for inventory statistics and reports.
    """
    permission_classes = [CanManageInventory]

    @extend_schema(
        summary="Get inventory overview",
        description="Get overall inventory statistics",
        responses={200: InventoryStatsSerializer},
        tags=['Inventory'],
    )
    def list(self, request):
        """Get inventory overview"""
        items = InventoryItem.objects.filter(is_active=True)

        total_value = sum(
            (item.quantity_on_hand * (item.product.cost_price or 0))
            for item in items
        )

        stats = {
            'total_products': items.values('product').distinct().count(),
            'total_items': items.count(),
            'total_warehouses': Warehouse.objects.filter(is_active=True).count(),
            'total_quantity': items.aggregate(total=Sum('quantity_on_hand'))['total'] or 0,
            'total_available': items.aggregate(total=Sum('quantity_available'))['total'] or 0,
            'total_reserved': items.aggregate(total=Sum('quantity_reserved'))['total'] or 0,
            'total_value': round(total_value, 2),
            'low_stock_count': items.filter(quantity_available__lte=F('reorder_level')).count(),
            'out_of_stock_count': items.filter(quantity_available=0).count(),
            'active_alerts': StockAlert.objects.filter(is_resolved=False).count(),
        }

        serializer = InventoryStatsSerializer(stats)
        return Response(serializer.data)

    @extend_schema(
        summary="Get low stock items",
        description="Get items that need reordering",
        tags=['Inventory'],
    )
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock items"""
        items = InventoryItem.objects.filter(
            is_active=True,
            quantity_available__lte=F('reorder_level')
        ).select_related('product', 'variant', 'warehouse')

        serializer = InventoryItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get out of stock items",
        description="Get items that are completely out of stock",
        tags=['Inventory'],
    )
    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get out of stock items"""
        items = InventoryItem.objects.filter(
            is_active=True,
            quantity_available=0
        ).select_related('product', 'variant', 'warehouse')

        serializer = InventoryItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)
