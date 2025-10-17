"""
Django Filters for Products App
"""
import django_filters
from django.db.models import Q
from .models import Product, ProductReview


class ProductFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Product model with advanced filtering options
    """
    # Price range filters
    min_price = django_filters.NumberFilter(method='filter_min_price', label='Minimum Price')
    max_price = django_filters.NumberFilter(method='filter_max_price', label='Maximum Price')

    # Boolean filters
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    is_digital = django_filters.BooleanFilter(field_name='is_digital')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock', label='In Stock')
    on_sale = django_filters.BooleanFilter(method='filter_on_sale', label='On Sale')

    # Rating filter
    min_rating = django_filters.NumberFilter(field_name='rating_average', lookup_expr='gte', label='Minimum Rating')

    # Product type filter
    product_type = django_filters.ChoiceFilter(
        field_name='product_type',
        choices=Product.PRODUCT_TYPES
    )

    # Multiple category filter
    categories = django_filters.CharFilter(method='filter_categories', label='Categories (comma-separated IDs)')

    # Multiple brand filter
    brands = django_filters.CharFilter(method='filter_brands', label='Brands (comma-separated IDs)')

    # Date range filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Product
        fields = [
            'category',
            'brand',
            'is_featured',
            'is_digital',
            'product_type',
        ]

    def filter_min_price(self, queryset, name, value):
        """
        Filter products with final price >= value
        Final price considers sale_price if available, otherwise regular_price
        """
        return queryset.filter(
            Q(sale_price__gte=value, sale_price__isnull=False) |
            Q(regular_price__gte=value, sale_price__isnull=True)
        )

    def filter_max_price(self, queryset, name, value):
        """
        Filter products with final price <= value
        """
        return queryset.filter(
            Q(sale_price__lte=value, sale_price__isnull=False) |
            Q(regular_price__lte=value, sale_price__isnull=True)
        )

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products that are in stock
        """
        if value:
            # Products with at least one inventory item with available quantity
            from inventory.models import InventoryItem
            in_stock_products = InventoryItem.objects.filter(
                quantity_available__gt=0
            ).values_list('product_id', flat=True)
            return queryset.filter(id__in=in_stock_products)
        return queryset

    def filter_on_sale(self, queryset, name, value):
        """
        Filter products that have a sale price
        """
        if value:
            return queryset.filter(sale_price__isnull=False)
        return queryset.filter(sale_price__isnull=True)

    def filter_categories(self, queryset, name, value):
        """
        Filter by multiple categories (comma-separated IDs)
        """
        try:
            category_ids = [int(id.strip()) for id in value.split(',')]
            return queryset.filter(category_id__in=category_ids)
        except (ValueError, AttributeError):
            return queryset

    def filter_brands(self, queryset, name, value):
        """
        Filter by multiple brands (comma-separated IDs)
        """
        try:
            brand_ids = [int(id.strip()) for id in value.split(',')]
            return queryset.filter(brand_id__in=brand_ids)
        except (ValueError, AttributeError):
            return queryset


class ProductReviewFilter(django_filters.FilterSet):
    """
    Filter for ProductReview model
    """
    # Basic filters
    product = django_filters.NumberFilter(field_name='product__id')
    customer = django_filters.NumberFilter(field_name='customer__id')
    rating = django_filters.NumberFilter(field_name='rating')

    # Boolean filters
    is_verified_purchase = django_filters.BooleanFilter(field_name='is_verified_purchase')
    is_approved = django_filters.BooleanFilter(field_name='is_approved')

    # Rating range
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')

    # Date range
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    # Helpful threshold
    min_helpful = django_filters.NumberFilter(field_name='helpful_count', lookup_expr='gte')

    class Meta:
        model = ProductReview
        fields = [
            'product',
            'customer',
            'rating',
            'is_verified_purchase',
            'is_approved',
        ]

