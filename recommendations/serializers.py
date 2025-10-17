from rest_framework import serializers
from .models import ProductInteraction, RecommendationLog
from products.serializers import ProductListSerializer


class ProductInteractionSerializer(serializers.ModelSerializer):
    """Product interaction serializer"""
    customer_name = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductInteraction
        fields = [
            'id', 'customer', 'customer_name', 'session_id',
            'product', 'product_name', 'interaction_type',
            'source', 'search_query', 'referrer_url',
            'duration_seconds', 'position', 'created_at'
        ]
        read_only_fields = ['customer', 'session_id', 'created_at']

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return 'Anonymous'


class TrackInteractionSerializer(serializers.Serializer):
    """Serializer for tracking product interactions"""
    product_id = serializers.IntegerField()
    interaction_type = serializers.ChoiceField(choices=ProductInteraction.INTERACTION_TYPES)
    source = serializers.CharField(max_length=50, required=False, allow_blank=True)
    search_query = serializers.CharField(max_length=500, required=False, allow_blank=True)
    referrer_url = serializers.URLField(required=False, allow_blank=True)
    duration_seconds = serializers.IntegerField(required=False, allow_null=True)
    position = serializers.IntegerField(required=False, allow_null=True)

    def validate_product_id(self, value):
        from products.models import Product
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive")
        return value


class RecommendationLogSerializer(serializers.ModelSerializer):
    """Recommendation log serializer"""
    customer_name = serializers.SerializerMethodField()
    source_product_name = serializers.CharField(source='source_product.name', read_only=True)
    click_through_rate = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationLog
        fields = [
            'id', 'customer', 'customer_name', 'session_id',
            'recommendation_type', 'recommended_products', 'source_product',
            'source_product_name', 'page_type', 'clicked_products',
            'conversion', 'click_through_rate', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return 'Anonymous'

    def get_click_through_rate(self, obj):
        if obj.recommended_products:
            total_recommended = len(obj.recommended_products)
            total_clicked = len(obj.clicked_products)
            if total_recommended > 0:
                return (total_clicked / total_recommended) * 100
        return 0


class RecommendationRequestSerializer(serializers.Serializer):
    """Serializer for requesting recommendations"""
    recommendation_type = serializers.ChoiceField(
        choices=['collaborative', 'content_based', 'trending', 'personalized'],
        default='personalized'
    )
    product_id = serializers.IntegerField(required=False, allow_null=True)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)
    exclude_products = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

    def validate(self, data):
        if data['recommendation_type'] == 'content_based' and not data.get('product_id'):
            raise serializers.ValidationError(
                "product_id is required for content-based recommendations"
            )
        return data


class RecommendationResponseSerializer(serializers.Serializer):
    """Serializer for recommendation response"""
    recommendation_type = serializers.CharField()
    products = ProductListSerializer(many=True)
    total_count = serializers.IntegerField()
    source_product_id = serializers.IntegerField(required=False, allow_null=True)


class SimilarProductsRequestSerializer(serializers.Serializer):
    """Serializer for requesting similar products"""
    product_id = serializers.IntegerField()
    limit = serializers.IntegerField(default=10, min_value=1, max_value=20)

    def validate_product_id(self, value):
        from products.models import Product
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive")
        return value


class TrendingProductsRequestSerializer(serializers.Serializer):
    """Serializer for requesting trending products"""
    days = serializers.IntegerField(default=7, min_value=1, max_value=90)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)
    category_id = serializers.IntegerField(required=False, allow_null=True)


class PersonalizedRecommendationsRequestSerializer(serializers.Serializer):
    """Serializer for requesting personalized recommendations"""
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)
    page_type = serializers.ChoiceField(
        choices=['homepage', 'product', 'cart', 'checkout'],
        default='homepage'
    )
    exclude_products = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class FrequentlyBoughtTogetherSerializer(serializers.Serializer):
    """Serializer for frequently bought together products"""
    product_id = serializers.IntegerField()
    limit = serializers.IntegerField(default=5, min_value=1, max_value=10)

    def validate_product_id(self, value):
        from products.models import Product
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or inactive")
        return value


class CustomerBehaviorSerializer(serializers.Serializer):
    """Serializer for customer behavior analysis"""
    customer_id = serializers.IntegerField()
    days = serializers.IntegerField(default=30, min_value=1, max_value=365)


class CustomerBehaviorResponseSerializer(serializers.Serializer):
    """Serializer for customer behavior response"""
    total_interactions = serializers.IntegerField()
    views = serializers.IntegerField()
    cart_adds = serializers.IntegerField()
    purchases = serializers.IntegerField()
    wishlist_adds = serializers.IntegerField()
    most_viewed_categories = serializers.ListField(child=serializers.DictField())
    favorite_brands = serializers.ListField(child=serializers.DictField())
    average_session_duration = serializers.FloatField()
    conversion_rate = serializers.FloatField()


class ProductPopularitySerializer(serializers.Serializer):
    """Serializer for product popularity metrics"""
    product_id = serializers.IntegerField()
    view_count = serializers.IntegerField()
    cart_count = serializers.IntegerField()
    purchase_count = serializers.IntegerField()
    wishlist_count = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    popularity_score = serializers.FloatField()


class RecommendationPerformanceSerializer(serializers.Serializer):
    """Serializer for recommendation engine performance"""
    total_recommendations_shown = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    click_through_rate = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    performance_by_type = serializers.DictField()
    top_performing_recommendations = serializers.ListField(child=serializers.DictField())


class SearchToProductSerializer(serializers.Serializer):
    """Serializer for search query to product mapping"""
    search_query = serializers.CharField(max_length=500)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=20)


class RecentlyViewedSerializer(serializers.Serializer):
    """Serializer for recently viewed products"""
    limit = serializers.IntegerField(default=10, min_value=1, max_value=20)
    exclude_products = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )

