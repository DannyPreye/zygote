"""
Django Filters for Promotions App
"""
import django_filters
from django.db import models
from django.utils import timezone
from .models import Promotion, Coupon


class PromotionFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Promotion model
    """
    # Discount type filter
    discount_type = django_filters.ChoiceFilter(
        field_name='discount_type',
        choices=Promotion.DISCOUNT_TYPES
    )

    # Apply to filter
    apply_to = django_filters.ChoiceFilter(
        field_name='apply_to',
        choices=Promotion.APPLY_TO
    )

    # Active status
    is_active = django_filters.BooleanFilter(field_name='is_active')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')

    # Date filters
    start_after = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_before = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    end_after = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='gte')
    end_before = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='lte')

    # Discount value filters
    min_discount = django_filters.NumberFilter(field_name='discount_value', lookup_expr='gte')
    max_discount = django_filters.NumberFilter(field_name='discount_value', lookup_expr='lte')

    # Usage filters
    min_used_count = django_filters.NumberFilter(field_name='used_count', lookup_expr='gte')
    max_used_count = django_filters.NumberFilter(field_name='used_count', lookup_expr='lte')

    # Priority filter
    min_priority = django_filters.NumberFilter(field_name='priority', lookup_expr='gte')

    # Search
    search = django_filters.CharFilter(method='filter_search')

    # Custom filters
    is_currently_active = django_filters.BooleanFilter(method='filter_currently_active')
    has_usage_left = django_filters.BooleanFilter(method='filter_has_usage_left')

    class Meta:
        model = Promotion
        fields = [
            'discount_type',
            'apply_to',
            'is_active',
            'is_featured',
        ]

    def filter_search(self, queryset, name, value):
        """Search in name and description"""
        return queryset.filter(
            name__icontains=value
        ) | queryset.filter(
            description__icontains=value
        )

    def filter_currently_active(self, queryset, name, value):
        """Filter promotions that are currently active"""
        now = timezone.now()
        if value:
            return queryset.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )
        return queryset.exclude(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

    def filter_has_usage_left(self, queryset, name, value):
        """Filter promotions with usage left"""
        from django.db.models import F
        if value:
            return queryset.filter(
                models.Q(max_uses__isnull=True) |
                models.Q(used_count__lt=F('max_uses'))
            )
        return queryset.filter(
            max_uses__isnull=False,
            used_count__gte=F('max_uses')
        )


class CouponFilter(django_filters.FilterSet):
    """
    Filter for Coupon model
    """
    # Promotion filter
    promotion = django_filters.NumberFilter(field_name='promotion__id')

    # Code filter
    code = django_filters.CharFilter(field_name='code', lookup_expr='icontains')

    # Customer filter
    customer = django_filters.NumberFilter(field_name='customer__id')

    # Usage filters
    is_single_use = django_filters.BooleanFilter(field_name='is_single_use')
    used = django_filters.BooleanFilter(field_name='used')

    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    used_after = django_filters.DateTimeFilter(field_name='used_at', lookup_expr='gte')
    used_before = django_filters.DateTimeFilter(field_name='used_at', lookup_expr='lte')

    # Custom filters
    is_valid = django_filters.BooleanFilter(method='filter_valid')

    class Meta:
        model = Coupon
        fields = [
            'promotion',
            'code',
            'customer',
            'is_single_use',
            'used',
        ]

    def filter_valid(self, queryset, name, value):
        """Filter valid/invalid coupons"""
        now = timezone.now()

        if value:
            # Valid coupons: not used (if single use) and promotion is active
            return queryset.filter(
                promotion__is_active=True,
                promotion__start_date__lte=now,
                promotion__end_date__gte=now
            ).filter(
                models.Q(is_single_use=False) |
                models.Q(is_single_use=True, used=False)
            )
        else:
            # Invalid coupons
            return queryset.exclude(
                promotion__is_active=True,
                promotion__start_date__lte=now,
                promotion__end_date__gte=now
            ) | queryset.filter(
                is_single_use=True,
                used=True
            )

