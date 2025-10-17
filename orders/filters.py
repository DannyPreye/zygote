"""
Django Filters for Orders App
"""
import django_filters
from django.db import models
from .models import Order, OrderItem


class OrderFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Order model
    """
    # Status filters
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=Order.STATUS_CHOICES
    )

    payment_status = django_filters.ChoiceFilter(
        field_name='payment_status',
        choices=Order.PAYMENT_STATUS_CHOICES
    )

    # Customer filters (for admin)
    customer = django_filters.NumberFilter(field_name='customer__id')
    customer_email = django_filters.CharFilter(field_name='customer__email', lookup_expr='icontains')
    guest_email = django_filters.CharFilter(field_name='guest_email', lookup_expr='icontains')

    # Order number filter
    order_number = django_filters.CharFilter(field_name='order_number', lookup_expr='icontains')

    # Amount filters
    min_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')

    # Payment method filter
    payment_method = django_filters.CharFilter(field_name='payment_method', lookup_expr='icontains')

    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    paid_after = django_filters.DateTimeFilter(field_name='paid_at', lookup_expr='gte')
    paid_before = django_filters.DateTimeFilter(field_name='paid_at', lookup_expr='lte')

    shipped_after = django_filters.DateTimeFilter(field_name='shipped_at', lookup_expr='gte')
    shipped_before = django_filters.DateTimeFilter(field_name='shipped_at', lookup_expr='lte')

    delivered_after = django_filters.DateTimeFilter(field_name='delivered_at', lookup_expr='gte')
    delivered_before = django_filters.DateTimeFilter(field_name='delivered_at', lookup_expr='lte')

    # Tracking filter
    tracking_number = django_filters.CharFilter(field_name='tracking_number', lookup_expr='icontains')
    carrier = django_filters.CharFilter(field_name='carrier', lookup_expr='icontains')

    # Currency filter
    currency = django_filters.CharFilter(field_name='currency', lookup_expr='iexact')

    # Has tracking
    has_tracking = django_filters.BooleanFilter(method='filter_has_tracking')

    # Is paid
    is_paid = django_filters.BooleanFilter(method='filter_is_paid')

    class Meta:
        model = Order
        fields = [
            'status',
            'payment_status',
            'customer',
            'order_number',
            'payment_method',
            'currency',
        ]

    def filter_has_tracking(self, queryset, name, value):
        """Filter orders with tracking number"""
        if value:
            return queryset.exclude(tracking_number='')
        return queryset.filter(tracking_number='')

    def filter_is_paid(self, queryset, name, value):
        """Filter paid orders"""
        if value:
            return queryset.filter(payment_status='paid')
        return queryset.exclude(payment_status='paid')


class OrderItemFilter(django_filters.FilterSet):
    """
    Filter for OrderItem model
    """
    # Order filter
    order = django_filters.NumberFilter(field_name='order__id')
    order_number = django_filters.CharFilter(field_name='order__order_number', lookup_expr='icontains')

    # Product filter
    product = django_filters.NumberFilter(field_name='product__id')
    product_name = django_filters.CharFilter(field_name='product_name', lookup_expr='icontains')
    product_sku = django_filters.CharFilter(field_name='product_sku', lookup_expr='icontains')

    # Variant filter
    variant = django_filters.NumberFilter(field_name='variant__id')

    # Quantity filters
    min_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    max_quantity = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')

    # Price filters
    min_price = django_filters.NumberFilter(field_name='unit_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='unit_price', lookup_expr='lte')

    # Fulfillment filter
    is_fulfilled = django_filters.BooleanFilter(method='filter_fulfilled')

    class Meta:
        model = OrderItem
        fields = [
            'order',
            'product',
            'variant',
        ]

    def filter_fulfilled(self, queryset, name, value):
        """Filter fulfilled items"""
        if value:
            return queryset.filter(fulfilled_quantity__gte=models.F('quantity'))
        return queryset.filter(fulfilled_quantity__lt=models.F('quantity'))

