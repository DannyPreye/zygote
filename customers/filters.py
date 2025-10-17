"""
Django Filters for Customers App
"""
import django_filters
from .models import Customer, Address


class CustomerFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Customer model
    """
    # Status filters
    is_active = django_filters.BooleanFilter(field_name='is_active')
    is_verified = django_filters.BooleanFilter(field_name='is_verified')
    is_vip = django_filters.BooleanFilter(field_name='is_vip')
    phone_verified = django_filters.BooleanFilter(field_name='phone_verified')

    # Loyalty tier filter
    loyalty_tier = django_filters.ChoiceFilter(
        field_name='loyalty_tier',
        choices=[
            ('bronze', 'Bronze'),
            ('silver', 'Silver'),
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
        ]
    )

    # Marketing preferences
    accepts_marketing_email = django_filters.BooleanFilter(field_name='accepts_marketing_email')
    accepts_marketing_sms = django_filters.BooleanFilter(field_name='accepts_marketing_sms')

    # Order stats filters
    min_orders = django_filters.NumberFilter(field_name='total_orders', lookup_expr='gte')
    max_orders = django_filters.NumberFilter(field_name='total_orders', lookup_expr='lte')

    min_spent = django_filters.NumberFilter(field_name='total_spent', lookup_expr='gte')
    max_spent = django_filters.NumberFilter(field_name='total_spent', lookup_expr='lte')

    # Date filters
    joined_after = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    joined_before = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')

    last_order_after = django_filters.DateTimeFilter(field_name='last_order_date', lookup_expr='gte')
    last_order_before = django_filters.DateTimeFilter(field_name='last_order_date', lookup_expr='lte')

    # Preferences
    preferred_language = django_filters.CharFilter(field_name='preferred_language')
    preferred_currency = django_filters.CharFilter(field_name='preferred_currency')

    # Gender filter
    gender = django_filters.CharFilter(field_name='gender', lookup_expr='iexact')

    class Meta:
        model = Customer
        fields = [
            'is_active',
            'is_verified',
            'is_vip',
            'phone_verified',
            'loyalty_tier',
            'accepts_marketing_email',
            'accepts_marketing_sms',
            'preferred_language',
            'preferred_currency',
            'gender',
        ]


class AddressFilter(django_filters.FilterSet):
    """
    Filter for Address model
    """
    # Address type filter
    address_type = django_filters.ChoiceFilter(
        field_name='address_type',
        choices=Address.ADDRESS_TYPES
    )

    # Default filter
    is_default = django_filters.BooleanFilter(field_name='is_default')

    # Location filters
    country = django_filters.CharFilter(field_name='country', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='state', lookup_expr='iexact')
    city = django_filters.CharFilter(field_name='city', lookup_expr='icontains')

    # Customer filter (for admin)
    customer = django_filters.NumberFilter(field_name='customer__id')

    class Meta:
        model = Address
        fields = [
            'address_type',
            'is_default',
            'country',
            'state',
            'city',
            'customer',
        ]

