from rest_framework import serializers
from .models import Cart, CartItem, Wishlist, WishlistItem
from products.serializers import ProductListSerializer, ProductVariantSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    product = ProductListSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    variant_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_id', 'variant', 'variant_id',
            'quantity', 'unit_price', 'subtotal', 'personalization',
            'added_at', 'updated_at'
        ]
        read_only_fields = ['added_at', 'updated_at']

    def get_subtotal(self, obj):
        price = obj.unit_price or obj.product.final_price
        if obj.variant:
            price = obj.variant.sale_price or obj.variant.price
        return price * obj.quantity

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        if value > 999:
            raise serializers.ValidationError("Quantity cannot exceed 999")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Shopping cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'uuid', 'customer', 'session_id', 'email', 'phone',
            'items', 'items_count', 'subtotal',
            'abandoned_email_sent', 'abandoned_email_sent_at',
            'recovered', 'recovered_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'customer', 'session_id', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()

    def get_subtotal(self, obj):
        total = 0
        for item in obj.items.all():
            price = item.unit_price or item.product.final_price
            if item.variant:
                price = item.variant.sale_price or item.variant.price
            total += price * item.quantity
        return total


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(default=1, min_value=1, max_value=999)
    personalization = serializers.JSONField(required=False, default=dict)

    def validate_product_id(self, value):
        from products.models import Product
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive")
        return value

    def validate_variant_id(self, value):
        if value:
            from products.models import ProductVariant
            if not ProductVariant.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError("Variant not found or inactive")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=0, max_value=999)


class WishlistItemSerializer(serializers.ModelSerializer):
    """Wishlist item serializer"""
    product = ProductListSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    variant_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = WishlistItem
        fields = [
            'id', 'product', 'product_id', 'variant', 'variant_id',
            'note', 'priority', 'added_at'
        ]
        read_only_fields = ['added_at']


class WishlistSerializer(serializers.ModelSerializer):
    """Wishlist serializer"""
    items = WishlistItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = [
            'id', 'customer', 'name', 'is_default', 'is_public',
            'items', 'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['customer', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()


class WishlistCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating wishlist"""
    class Meta:
        model = Wishlist
        fields = ['name', 'is_public']


class AddToWishlistSerializer(serializers.Serializer):
    """Serializer for adding items to wishlist"""
    wishlist_id = serializers.IntegerField(required=False)
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.IntegerField(default=0)

