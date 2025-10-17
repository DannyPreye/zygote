from rest_framework import serializers
from django.utils import timezone
from .models import Promotion, Coupon, CouponUsage


class PromotionListSerializer(serializers.ModelSerializer):
    """Minimal promotion serializer for lists"""
    is_active_now = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'uuid', 'name', 'discount_type', 'discount_value',
            'start_date', 'end_date', 'is_active', 'is_active_now',
            'is_featured', 'used_count', 'max_uses', 'usage_percentage'
        ]

    def get_is_active_now(self, obj):
        now = timezone.now()
        return (obj.is_active and
                obj.start_date <= now <= obj.end_date)

    def get_usage_percentage(self, obj):
        if obj.max_uses:
            return (obj.used_count / obj.max_uses) * 100
        return 0


class PromotionDetailSerializer(serializers.ModelSerializer):
    """Detailed promotion serializer"""
    products_count = serializers.SerializerMethodField()
    categories_count = serializers.SerializerMethodField()
    brands_count = serializers.SerializerMethodField()
    customer_groups_count = serializers.SerializerMethodField()
    is_active_now = serializers.SerializerMethodField()
    remaining_uses = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'uuid', 'name', 'description',
            'discount_type', 'discount_value', 'apply_to',
            'products', 'categories', 'brands', 'customer_groups',
            'products_count', 'categories_count', 'brands_count', 'customer_groups_count',
            'min_quantity', 'min_purchase_amount',
            'max_uses', 'max_uses_per_customer', 'used_count', 'remaining_uses',
            'start_date', 'end_date', 'is_active', 'is_active_now',
            'is_featured', 'priority',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'used_count', 'created_at', 'updated_at']

    def get_products_count(self, obj):
        return obj.products.count()

    def get_categories_count(self, obj):
        return obj.categories.count()

    def get_brands_count(self, obj):
        return obj.brands.count()

    def get_customer_groups_count(self, obj):
        return obj.customer_groups.count()

    def get_is_active_now(self, obj):
        now = timezone.now()
        return (obj.is_active and
                obj.start_date <= now <= obj.end_date)

    def get_remaining_uses(self, obj):
        if obj.max_uses:
            return max(0, obj.max_uses - obj.used_count)
        return None


class PromotionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating promotions"""
    class Meta:
        model = Promotion
        fields = [
            'name', 'description', 'discount_type', 'discount_value', 'apply_to',
            'products', 'categories', 'brands', 'customer_groups',
            'min_quantity', 'min_purchase_amount',
            'max_uses', 'max_uses_per_customer',
            'start_date', 'end_date', 'is_active', 'is_featured', 'priority'
        ]

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")

        if data['discount_type'] == 'percentage' and data['discount_value'] > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%")

        if data['discount_value'] < 0:
            raise serializers.ValidationError("Discount value must be positive")

        # Validate application targets
        if data['apply_to'] == 'specific_products' and not data.get('products'):
            raise serializers.ValidationError("Products are required for specific product promotions")

        if data['apply_to'] == 'specific_categories' and not data.get('categories'):
            raise serializers.ValidationError("Categories are required for specific category promotions")

        if data['apply_to'] == 'specific_brands' and not data.get('brands'):
            raise serializers.ValidationError("Brands are required for specific brand promotions")

        return data


class CouponSerializer(serializers.ModelSerializer):
    """Coupon serializer"""
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    discount_type = serializers.CharField(source='promotion.discount_type', read_only=True)
    discount_value = serializers.DecimalField(
        source='promotion.discount_value',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'uuid', 'code', 'promotion', 'promotion_name',
            'discount_type', 'discount_value',
            'is_single_use', 'customer', 'used', 'used_at', 'used_by',
            'is_valid', 'created_at'
        ]
        read_only_fields = ['uuid', 'used', 'used_at', 'used_by', 'created_at']

    def get_is_valid(self, obj):
        if obj.used and obj.is_single_use:
            return False

        now = timezone.now()
        return (obj.promotion.is_active and
                obj.promotion.start_date <= now <= obj.promotion.end_date)


class CouponCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating coupons"""
    class Meta:
        model = Coupon
        fields = ['code', 'promotion', 'is_single_use', 'customer']

    def validate_code(self, value):
        if Coupon.objects.filter(code=value.upper()).exists():
            raise serializers.ValidationError("A coupon with this code already exists")
        return value.upper()


class ValidateCouponSerializer(serializers.Serializer):
    """Serializer for validating coupon codes"""
    code = serializers.CharField(max_length=50)
    cart_total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    cart_quantity = serializers.IntegerField(required=False)


class CouponValidationResponseSerializer(serializers.Serializer):
    """Serializer for coupon validation response"""
    is_valid = serializers.BooleanField()
    message = serializers.CharField()
    discount_type = serializers.CharField(required=False)
    discount_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )
    min_purchase_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False
    )


class CouponUsageSerializer(serializers.ModelSerializer):
    """Coupon usage history serializer"""
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    customer_name = serializers.SerializerMethodField()
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon', 'coupon_code', 'customer', 'customer_name',
            'order', 'order_number', 'discount_amount', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return None


class ApplyCouponSerializer(serializers.Serializer):
    """Serializer for applying coupon to order"""
    coupon_code = serializers.CharField(max_length=50)
    order_id = serializers.IntegerField()

    def validate_coupon_code(self, value):
        return value.upper()


class PromotionStatsSerializer(serializers.Serializer):
    """Serializer for promotion statistics"""
    total_promotions = serializers.IntegerField()
    active_promotions = serializers.IntegerField()
    total_discounts_given = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_coupons_used = serializers.IntegerField()
    most_used_promotion = serializers.CharField()

