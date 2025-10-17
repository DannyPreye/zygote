"""
Django Filters for Payments App
"""
import django_filters
from .models import Payment, Refund


class PaymentFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Payment model
    """
    # Status filter
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=Payment.PAYMENT_STATUS
    )

    # Gateway filter
    gateway = django_filters.ChoiceFilter(
        field_name='gateway',
        choices=[
            ('stripe', 'Stripe'),
            ('paystack', 'Paystack'),
            ('paypal', 'PayPal'),
        ]
    )

    # Payment method filter
    payment_method = django_filters.CharFilter(field_name='payment_method', lookup_expr='iexact')

    # Order filter
    order = django_filters.NumberFilter(field_name='order__id')
    order_number = django_filters.CharFilter(field_name='order__order_number', lookup_expr='icontains')

    # Customer filter (for admin)
    customer = django_filters.NumberFilter(field_name='order__customer__id')
    customer_email = django_filters.CharFilter(field_name='order__customer__email', lookup_expr='icontains')

    # Amount filters
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    # Currency filter
    currency = django_filters.CharFilter(field_name='currency', lookup_expr='iexact')

    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    completed_after = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')

    # Transaction ID filter
    transaction_id = django_filters.CharFilter(field_name='transaction_id', lookup_expr='icontains')

    # Success filter
    is_successful = django_filters.BooleanFilter(method='filter_successful')

    class Meta:
        model = Payment
        fields = [
            'status',
            'gateway',
            'payment_method',
            'order',
            'currency',
        ]

    def filter_successful(self, queryset, name, value):
        """Filter successful payments"""
        if value:
            return queryset.filter(status='succeeded')
        return queryset.exclude(status='succeeded')


class RefundFilter(django_filters.FilterSet):
    """
    Filter for Refund model
    """
    # Status filter
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=Refund.REFUND_STATUS
    )

    # Reason filter
    reason = django_filters.ChoiceFilter(
        field_name='reason',
        choices=Refund.REFUND_REASONS
    )

    # Payment filter
    payment = django_filters.NumberFilter(field_name='payment__id')
    transaction_id = django_filters.CharFilter(field_name='payment__transaction_id', lookup_expr='icontains')

    # Amount filters
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    # Created by filter
    created_by = django_filters.NumberFilter(field_name='created_by__id')

    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    completed_after = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_before = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')

    class Meta:
        model = Refund
        fields = [
            'status',
            'reason',
            'payment',
            'created_by',
        ]

