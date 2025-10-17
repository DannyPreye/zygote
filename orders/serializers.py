from rest_framework import serializers
from .models import Order, OrderItem, ShippingZone, ShippingMethod
from customers.serializers import CustomerListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'variant', 'product_name', 'product_sku',
            'variant_name', 'product_image', 'quantity', 'unit_price',
            'unit_cost', 'total_price', 'tax_amount', 'discount_amount',
            'fulfilled_quantity', 'refunded_quantity',
            'download_url', 'download_count', 'download_expiry'
        ]
        read_only_fields = ['product_name', 'product_sku', 'variant_name',
                           'product_image', 'download_count']


class OrderListSerializer(serializers.ModelSerializer):
    """Order list serializer"""
    customer_name = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'order_number', 'customer', 'customer_name',
            'status', 'payment_status', 'total_amount', 'currency',
            'items_count', 'created_at', 'paid_at'
        ]

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return obj.guest_email

    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order serializer"""
    customer = CustomerListSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    can_cancel = serializers.SerializerMethodField()
    can_refund = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'uuid', 'order_number', 'customer', 'guest_email',
            'status', 'payment_status',
            'subtotal', 'tax_amount', 'shipping_amount', 'discount_amount',
            'total_amount', 'refunded_amount', 'currency', 'exchange_rate',
            'payment_method', 'payment_gateway', 'transaction_id',
            'shipping_method', 'carrier', 'tracking_number', 'estimated_delivery_date',
            'billing_address', 'shipping_address',
            'coupon', 'coupon_code', 'customer_notes', 'admin_notes', 'gift_message',
            'ip_address', 'user_agent', 'referrer',
            'utm_source', 'utm_medium', 'utm_campaign',
            'is_gift', 'requires_shipping',
            'items', 'can_cancel', 'can_refund',
            'created_at', 'updated_at', 'paid_at', 'shipped_at',
            'delivered_at', 'cancelled_at'
        ]
        read_only_fields = [
            'uuid', 'order_number', 'customer', 'subtotal', 'total_amount',
            'refunded_amount', 'transaction_id', 'ip_address', 'user_agent',
            'created_at', 'updated_at', 'paid_at', 'shipped_at',
            'delivered_at', 'cancelled_at'
        ]

    def get_can_cancel(self, obj):
        return obj.status in ['pending', 'processing', 'on_hold']

    def get_can_refund(self, obj):
        return obj.payment_status == 'paid' and obj.status not in ['refunded', 'cancelled']


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    billing_address = serializers.JSONField()
    shipping_address = serializers.JSONField()
    payment_method = serializers.CharField(max_length=50)
    shipping_method = serializers.CharField(max_length=100)
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    is_gift = serializers.BooleanField(default=False)
    gift_message = serializers.CharField(required=False, allow_blank=True)
    guest_email = serializers.EmailField(required=False, allow_blank=True)

    def validate_billing_address(self, value):
        required_fields = ['first_name', 'last_name', 'address_line1',
                          'city', 'state', 'postal_code', 'country']
        for field in required_fields:
            if field not in value or not value[field]:
                raise serializers.ValidationError(f"{field} is required")
        return value

    def validate_shipping_address(self, value):
        required_fields = ['first_name', 'last_name', 'address_line1',
                          'city', 'state', 'postal_code', 'country']
        for field in required_fields:
            if field not in value or not value[field]:
                raise serializers.ValidationError(f"{field} is required")
        return value

    def validate(self, data):
        request = self.context.get('request')
        if not request.user.is_authenticated and not data.get('guest_email'):
            raise serializers.ValidationError("Guest email is required for guest checkout")
        return data


class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    send_notification = serializers.BooleanField(default=True)


class OrderTrackingSerializer(serializers.Serializer):
    """Serializer for order tracking info"""
    carrier = serializers.CharField(max_length=100)
    tracking_number = serializers.CharField(max_length=100)
    estimated_delivery_date = serializers.DateField(required=False, allow_null=True)


class ShippingMethodSerializer(serializers.ModelSerializer):
    """Shipping method serializer"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    delivery_time = serializers.SerializerMethodField()

    class Meta:
        model = ShippingMethod
        fields = [
            'id', 'zone', 'zone_name', 'name', 'code', 'carrier',
            'min_delivery_days', 'max_delivery_days', 'delivery_time',
            'delivery_time_description', 'pricing_type', 'flat_rate',
            'min_order_amount', 'max_order_amount',
            'min_weight', 'max_weight', 'rate_table',
            'is_active', 'display_order'
        ]
        read_only_fields = ['display_order']

    def get_delivery_time(self, obj):
        if obj.delivery_time_description:
            return obj.delivery_time_description
        return f"{obj.min_delivery_days}-{obj.max_delivery_days} days"


class ShippingZoneSerializer(serializers.ModelSerializer):
    """Shipping zone serializer"""
    methods = ShippingMethodSerializer(many=True, read_only=True)
    methods_count = serializers.SerializerMethodField()

    class Meta:
        model = ShippingZone
        fields = [
            'id', 'name', 'countries', 'states', 'postal_codes',
            'is_active', 'methods', 'methods_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_methods_count(self, obj):
        return obj.methods.filter(is_active=True).count()


class CalculateShippingSerializer(serializers.Serializer):
    """Serializer for calculating shipping costs"""
    country = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    cart_weight = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class OrderSummarySerializer(serializers.Serializer):
    """Serializer for order summary before checkout"""
    items = OrderItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

