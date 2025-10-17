from rest_framework import serializers
from .models import (
    Category, Brand, Product, ProductImage, ProductVariant,
    Tag, ProductReview
)


class CategorySerializer(serializers.ModelSerializer):
    """Basic category serializer"""
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'uuid', 'name', 'slug', 'parent', 'description',
            'image', 'icon', 'meta_title', 'meta_description', 'meta_keywords',
            'display_order', 'is_active', 'is_featured', 'show_in_menu',
            'children_count', 'products_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'created_at', 'updated_at']

    def get_children_count(self, obj):
        return obj.children.count()

    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()


class CategoryListSerializer(serializers.ModelSerializer):
    """Minimal category serializer for lists"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'icon']


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Nested category tree"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'children']

    def get_children(self, obj):
        if obj.children.exists():
            return CategoryTreeSerializer(obj.children.filter(is_active=True), many=True).data
        return []


class BrandSerializer(serializers.ModelSerializer):
    """Brand serializer"""
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            'id', 'uuid', 'name', 'slug', 'logo', 'website', 'description',
            'is_active', 'is_featured', 'products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()


class BrandListSerializer(serializers.ModelSerializer):
    """Minimal brand serializer for lists"""
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo']


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer"""
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt_text', 'is_primary', 'order']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ProductVariantSerializer(serializers.ModelSerializer):
    """Product variant serializer"""
    images = ProductImageSerializer(many=True, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'uuid', 'sku', 'name', 'attributes',
            'price', 'sale_price', 'final_price', 'cost_price',
            'weight', 'dimensions', 'is_active', 'is_default',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_final_price(self, obj):
        return obj.sale_price if obj.sale_price else obj.price


class ProductListSerializer(serializers.ModelSerializer):
    """Optimized product serializer for list views"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, allow_null=True)
    primary_image = serializers.SerializerMethodField()
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_on_sale = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'uuid', 'name', 'slug', 'sku', 'product_type',
            'category_name', 'brand_name', 'primary_image',
            'regular_price', 'sale_price', 'final_price', 'is_on_sale',
            'is_featured', 'is_new', 'rating_average', 'rating_count',
            'sales_count', 'created_at'
        ]

    def get_primary_image(self, obj):
        request = self.context.get('request')
        image = obj.images.filter(is_primary=True).first()
        if image and request:
            return request.build_absolute_uri(image.image.url)
        return None

    def get_is_on_sale(self, obj):
        return obj.sale_price is not None and obj.sale_price < obj.regular_price


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer"""
    category = CategoryListSerializer(read_only=True)
    brand = BrandListSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_on_sale = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    average_rating = serializers.DecimalField(source='rating_average', max_digits=3, decimal_places=2, read_only=True)
    total_reviews = serializers.IntegerField(source='rating_count', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'uuid', 'name', 'slug', 'sku', 'barcode', 'product_type',
            'category', 'brand', 'tags', 'short_description', 'description', 'specifications',
            'cost_price', 'regular_price', 'sale_price', 'final_price', 'is_on_sale',
            'sale_start_date', 'sale_end_date', 'tax_class', 'is_taxable',
            'weight', 'dimensions', 'shipping_class',
            'is_digital', 'download_limit', 'download_expiry_days',
            'is_active', 'is_featured', 'is_new', 'visibility',
            'meta_title', 'meta_description', 'meta_keywords', 'canonical_url',
            'view_count', 'sales_count', 'wishlist_count',
            'average_rating', 'total_reviews', 'is_in_stock',
            'images', 'variants', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'view_count', 'sales_count',
                           'wishlist_count', 'created_at', 'updated_at']

    def get_is_on_sale(self, obj):
        return obj.sale_price is not None and obj.sale_price < obj.regular_price

    def get_is_in_stock(self, obj):
        # This would check inventory in a real implementation
        return True


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'product_type', 'category', 'brand',
            'short_description', 'description', 'specifications',
            'cost_price', 'regular_price', 'sale_price',
            'sale_start_date', 'sale_end_date', 'tax_class', 'is_taxable',
            'weight', 'dimensions', 'shipping_class',
            'is_digital', 'digital_file', 'download_limit', 'download_expiry_days',
            'is_active', 'is_featured', 'is_new', 'visibility',
            'meta_title', 'meta_description', 'meta_keywords'
        ]

    def validate(self, data):
        if data.get('sale_price') and data.get('regular_price'):
            if data['sale_price'] >= data['regular_price']:
                raise serializers.ValidationError("Sale price must be less than regular price")
        return data


class ProductReviewSerializer(serializers.ModelSerializer):
    """Product review serializer"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_avatar = serializers.ImageField(source='customer.avatar', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'customer', 'customer_name', 'customer_avatar',
            'order_item', 'rating', 'title', 'comment', 'images',
            'is_verified_purchase', 'is_approved', 'is_featured',
            'helpful_count', 'not_helpful_count',
            'admin_response', 'admin_response_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['customer', 'is_verified_purchase', 'is_approved',
                           'helpful_count', 'not_helpful_count', 'admin_response',
                           'admin_response_date', 'created_at', 'updated_at']


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    class Meta:
        model = ProductReview
        fields = ['product', 'rating', 'title', 'comment', 'images']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

