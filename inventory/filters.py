"""
Django Filters for Inventory App
"""
import django_filters
from django.db.models import F
from .models import InventoryItem, StockMovement, PurchaseOrder


class InventoryItemFilter(django_filters.FilterSet):
    """
    Comprehensive filter for InventoryItem model
    """
    # Warehouse filter
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')
    warehouse_code = django_filters.CharFilter(field_name='warehouse__code', lookup_expr='iexact')

    # Product filter
    product = django_filters.NumberFilter(field_name='product__id')
    variant = django_filters.NumberFilter(field_name='variant__id')
    product_sku = django_filters.CharFilter(field_name='product__sku', lookup_expr='icontains')

    # Stock level filters
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label='Low Stock Items')
    out_of_stock = django_filters.BooleanFilter(method='filter_out_of_stock', label='Out of Stock Items')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock', label='In Stock Items')

    min_quantity = django_filters.NumberFilter(field_name='quantity_available', lookup_expr='gte')
    max_quantity = django_filters.NumberFilter(field_name='quantity_available', lookup_expr='lte')

    # Active filter
    is_active = django_filters.BooleanFilter(field_name='is_active')

    # Last counted filter
    last_counted_after = django_filters.DateTimeFilter(field_name='last_counted_at', lookup_expr='gte')
    last_counted_before = django_filters.DateTimeFilter(field_name='last_counted_at', lookup_expr='lte')

    class Meta:
        model = InventoryItem
        fields = [
            'warehouse',
            'product',
            'variant',
            'is_active',
        ]

    def filter_low_stock(self, queryset, name, value):
        """Filter items with low stock (below reorder level)"""
        if value:
            return queryset.filter(quantity_available__lte=F('reorder_level'))
        return queryset

    def filter_out_of_stock(self, queryset, name, value):
        """Filter items that are out of stock"""
        if value:
            return queryset.filter(quantity_available=0)
        return queryset.filter(quantity_available__gt=0)

    def filter_in_stock(self, queryset, name, value):
        """Filter items that are in stock"""
        if value:
            return queryset.filter(quantity_available__gt=0)
        return queryset.filter(quantity_available=0)


class StockMovementFilter(django_filters.FilterSet):
    """
    Filter for StockMovement model
    """
    # Inventory item filter
    inventory_item = django_filters.NumberFilter(field_name='inventory_item__id')
    warehouse = django_filters.NumberFilter(field_name='inventory_item__warehouse__id')
    product = django_filters.NumberFilter(field_name='inventory_item__product__id')

    # Movement type filter
    movement_type = django_filters.ChoiceFilter(
        field_name='movement_type',
        choices=StockMovement.MOVEMENT_TYPES
    )

    # Reference filters
    reference_type = django_filters.CharFilter(field_name='reference_type', lookup_expr='iexact')
    reference_id = django_filters.NumberFilter(field_name='reference_id')

    # User filter
    user = django_filters.NumberFilter(field_name='user__id')

    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    # Quantity range
    min_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    max_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')

    class Meta:
        model = StockMovement
        fields = [
            'inventory_item',
            'movement_type',
            'reference_type',
            'user',
        ]


class PurchaseOrderFilter(django_filters.FilterSet):
    """
    Filter for PurchaseOrder model
    """
    # Status filter
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=PurchaseOrder.STATUS_CHOICES
    )

    # Supplier filter
    supplier = django_filters.NumberFilter(field_name='supplier__id')
    supplier_name = django_filters.CharFilter(field_name='supplier__name', lookup_expr='icontains')

    # Warehouse filter
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')

    # PO number filter
    po_number = django_filters.CharFilter(field_name='po_number', lookup_expr='icontains')

    # Date filters
    order_date_after = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    order_date_before = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')

    expected_delivery_after = django_filters.DateFilter(field_name='expected_delivery_date', lookup_expr='gte')
    expected_delivery_before = django_filters.DateFilter(field_name='expected_delivery_date', lookup_expr='lte')

    # Amount filters
    min_amount = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')

    # Created by filter
    created_by = django_filters.NumberFilter(field_name='created_by__id')

    class Meta:
        model = PurchaseOrder
        fields = [
            'status',
            'supplier',
            'warehouse',
            'created_by',
        ]

