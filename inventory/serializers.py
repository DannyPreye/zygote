from rest_framework import serializers
from .models import (
    Warehouse, InventoryItem, StockMovement, StockAlert,
    Supplier, PurchaseOrder, PurchaseOrderItem
)


class WarehouseSerializer(serializers.ModelSerializer):
    """Warehouse serializer"""
    manager_name = serializers.SerializerMethodField()
    capacity_percentage = serializers.SerializerMethodField()
    inventory_count = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            'id', 'uuid', 'name', 'code', 'address', 'city', 'state',
            'country', 'postal_code', 'latitude', 'longitude',
            'phone', 'email', 'manager', 'manager_name',
            'is_active', 'is_default', 'can_ship', 'can_receive',
            'max_capacity', 'current_capacity', 'capacity_percentage',
            'operating_hours', 'inventory_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'current_capacity', 'created_at', 'updated_at']

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name() or obj.manager.username
        return None

    def get_capacity_percentage(self, obj):
        if obj.max_capacity and obj.max_capacity > 0:
            return (obj.current_capacity / obj.max_capacity) * 100
        return 0

    def get_inventory_count(self, obj):
        return InventoryItem.objects.filter(warehouse=obj, is_active=True).count()


class WarehouseListSerializer(serializers.ModelSerializer):
    """Minimal warehouse serializer for lists"""
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'code', 'city', 'country', 'is_active', 'is_default']


class InventoryItemSerializer(serializers.ModelSerializer):
    """Inventory item serializer"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True, allow_null=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    stock_status = serializers.SerializerMethodField()
    needs_reorder = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'variant', 'variant_name', 'warehouse', 'warehouse_name',
            'quantity_on_hand', 'quantity_reserved', 'quantity_available',
            'quantity_incoming', 'reorder_level', 'reorder_quantity',
            'max_stock_level', 'bin_location', 'aisle', 'shelf',
            'batch_number', 'expiry_date', 'last_counted_at', 'last_restocked_at',
            'average_cost', 'last_purchase_cost', 'is_active',
            'stock_status', 'needs_reorder',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['quantity_available', 'created_at', 'updated_at']

    def get_stock_status(self, obj):
        if obj.quantity_available <= 0:
            return 'out_of_stock'
        elif obj.quantity_available <= obj.reorder_level:
            return 'low_stock'
        elif obj.max_stock_level and obj.quantity_available >= obj.max_stock_level:
            return 'overstock'
        return 'in_stock'

    def get_needs_reorder(self, obj):
        return obj.quantity_available <= obj.reorder_level


class InventoryItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating inventory items"""
    class Meta:
        model = InventoryItem
        fields = [
            'reorder_level', 'reorder_quantity', 'max_stock_level',
            'bin_location', 'aisle', 'shelf', 'batch_number',
            'expiry_date', 'is_active'
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    """Stock movement serializer"""
    product_name = serializers.CharField(source='inventory_item.product.name', read_only=True)
    product_sku = serializers.CharField(source='inventory_item.product.sku', read_only=True)
    warehouse_name = serializers.CharField(source='inventory_item.warehouse.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    from_warehouse_name = serializers.CharField(source='from_warehouse.name', read_only=True)
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'uuid', 'inventory_item', 'product_name', 'product_sku',
            'warehouse_name', 'movement_type', 'quantity',
            'reference_type', 'reference_id',
            'from_warehouse', 'from_warehouse_name',
            'to_warehouse', 'to_warehouse_name',
            'unit_cost', 'total_cost', 'notes', 'user', 'user_name',
            'created_at'
        ]
        read_only_fields = ['uuid', 'user', 'created_at']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None


class StockMovementCreateSerializer(serializers.Serializer):
    """Serializer for creating stock movements"""
    inventory_item_id = serializers.IntegerField()
    movement_type = serializers.ChoiceField(choices=StockMovement.MOVEMENT_TYPES)
    quantity = serializers.IntegerField()
    reference_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    reference_id = serializers.IntegerField(required=False, allow_null=True)
    from_warehouse_id = serializers.IntegerField(required=False, allow_null=True)
    to_warehouse_id = serializers.IntegerField(required=False, allow_null=True)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['movement_type'] == 'transfer':
            if not data.get('from_warehouse_id') or not data.get('to_warehouse_id'):
                raise serializers.ValidationError(
                    "From and to warehouses are required for transfers"
                )
        return data


class StockAlertSerializer(serializers.ModelSerializer):
    """Stock alert serializer"""
    product_name = serializers.CharField(source='inventory_item.product.name', read_only=True)
    product_sku = serializers.CharField(source='inventory_item.product.sku', read_only=True)
    warehouse_name = serializers.CharField(source='inventory_item.warehouse.name', read_only=True)
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockAlert
        fields = [
            'id', 'inventory_item', 'product_name', 'product_sku',
            'warehouse_name', 'alert_type', 'threshold_value', 'current_value',
            'is_resolved', 'resolved_at', 'resolved_by', 'resolved_by_name',
            'created_at'
        ]
        read_only_fields = ['created_at']

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.get_full_name() or obj.resolved_by.username
        return None


class SupplierSerializer(serializers.ModelSerializer):
    """Supplier serializer"""
    purchase_orders_count = serializers.SerializerMethodField()
    total_purchase_value = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'uuid', 'name', 'code', 'contact_person', 'email',
            'phone', 'website', 'address', 'city', 'state', 'country',
            'postal_code', 'tax_id', 'payment_terms', 'lead_time_days',
            'minimum_order_value', 'rating', 'notes', 'is_active',
            'purchase_orders_count', 'total_purchase_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_purchase_orders_count(self, obj):
        return obj.purchase_orders.count()

    def get_total_purchase_value(self, obj):
        total = sum(po.total_amount for po in obj.purchase_orders.filter(
            status__in=['confirmed', 'received']
        ))
        return total


class SupplierListSerializer(serializers.ModelSerializer):
    """Minimal supplier serializer for lists"""
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'code', 'contact_person', 'email', 'phone', 'is_active']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Purchase order item serializer"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True, allow_null=True)
    received_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'product', 'product_name', 'product_sku',
            'variant', 'variant_name', 'quantity_ordered', 'quantity_received',
            'received_percentage', 'unit_cost', 'total_cost', 'notes'
        ]

    def get_received_percentage(self, obj):
        if obj.quantity_ordered > 0:
            return (obj.quantity_received / obj.quantity_ordered) * 100
        return 0


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Purchase order serializer"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'uuid', 'po_number', 'supplier', 'supplier_name',
            'warehouse', 'warehouse_name', 'status',
            'order_date', 'expected_delivery_date', 'actual_delivery_date',
            'subtotal', 'tax_amount', 'shipping_amount', 'total_amount',
            'payment_status', 'payment_terms', 'notes',
            'created_by', 'created_by_name', 'approved_by', 'approved_by_name',
            'items', 'items_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'po_number', 'order_date', 'created_by',
            'approved_by', 'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

    def get_items_count(self, obj):
        return obj.items.count()


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Minimal purchase order serializer for lists"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'uuid', 'po_number', 'supplier_name', 'status',
            'total_amount', 'expected_delivery_date', 'created_at'
        ]


class PurchaseOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating purchase orders"""
    supplier_id = serializers.IntegerField()
    warehouse_id = serializers.IntegerField()
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    payment_terms = serializers.CharField(max_length=200, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )

    def validate_items(self, value):
        for item in value:
            if 'product_id' not in item or 'quantity_ordered' not in item or 'unit_cost' not in item:
                raise serializers.ValidationError(
                    "Each item must have product_id, quantity_ordered, and unit_cost"
                )
        return value


class InventoryStatsSerializer(serializers.Serializer):
    """Serializer for inventory statistics"""
    total_products = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    low_stock_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()
    overstock_count = serializers.IntegerField()
    warehouses_count = serializers.IntegerField()

