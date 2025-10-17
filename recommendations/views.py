"""
Recommendation Engine Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging
from datetime import timedelta
from collections import defaultdict

from .models import ProductInteraction, RecommendationLog
from .serializers import (
    ProductInteractionSerializer,
    TrackInteractionSerializer,
    RecommendationLogSerializer,
    RecommendationRequestSerializer,
    RecommendationResponseSerializer,
    SimilarProductsRequestSerializer,
    TrendingProductsRequestSerializer,
    PersonalizedRecommendationsRequestSerializer,
    FrequentlyBoughtTogetherSerializer,
    CustomerBehaviorSerializer,
    CustomerBehaviorResponseSerializer,
    ProductPopularitySerializer,
    RecommendationPerformanceSerializer,
    SearchToProductSerializer,
    RecentlyViewedSerializer,
)
from products.models import Product
from products.serializers import ProductListSerializer
from api.permissions import CanManageOrders

logger = logging.getLogger(__name__)


# ============================================================================
# RECOMMENDATION ENGINE CORE
# ============================================================================

class RecommendationEngine:
    """
    AI-powered recommendation engine using collaborative and content-based filtering
    """

    def __init__(self):
        self.interaction_weights = {
            'view': 1.0,
            'click': 1.5,
            'cart': 3.0,
            'wishlist': 2.0,
            'purchase': 5.0,
            'review': 2.5,
            'share': 2.0,
            'search': 1.0,
        }

    def get_collaborative_recommendations(self, customer_id, limit=10, exclude_products=None):
        """
        Collaborative filtering: Users who liked X also liked Y
        """
        cache_key = f'collab_rec_{customer_id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        exclude_products = exclude_products or []

        # Get customer's purchased/interacted products
        customer_products = set(
            ProductInteraction.objects.filter(
                customer_id=customer_id,
                interaction_type__in=['purchase', 'cart', 'wishlist']
            ).values_list('product_id', flat=True)
        )

        if not customer_products:
            return []

        # Find similar customers (who interacted with same products)
        similar_customers = ProductInteraction.objects.filter(
            product_id__in=customer_products,
            interaction_type__in=['purchase', 'cart']
        ).exclude(
            customer_id=customer_id
        ).values_list('customer_id', flat=True).distinct()[:100]

        # Get products these similar customers liked
        product_scores = defaultdict(float)

        interactions = ProductInteraction.objects.filter(
            customer_id__in=similar_customers
        ).exclude(
            product_id__in=customer_products
        ).exclude(
            product_id__in=exclude_products
        ).values('product_id', 'interaction_type')

        for interaction in interactions:
            weight = self.interaction_weights.get(interaction['interaction_type'], 1.0)
            product_scores[interaction['product_id']] += weight

        # Sort by score and return top products
        sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
        product_ids = [p[0] for p in sorted_products[:limit]]

        cache.set(cache_key, product_ids, 1800)  # Cache for 30 minutes
        return product_ids

    def get_content_based_recommendations(self, product_id, limit=10):
        """
        Content-based filtering: Products similar to this one
        """
        cache_key = f'content_rec_{product_id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            product = Product.objects.select_related('category', 'brand').get(id=product_id)
        except Product.DoesNotExist:
            return []

        # Find similar products based on category, brand, and tags
        similar_products = Product.objects.filter(
            is_active=True
        ).exclude(
            id=product_id
        )

        # Prioritize same category
        similar_products = similar_products.filter(
            Q(category=product.category) |
            Q(brand=product.brand)
        )

        # Order by rating and sales
        similar_products = similar_products.order_by(
            '-rating_average',
            '-sales_count'
        )[:limit]

        product_ids = list(similar_products.values_list('id', flat=True))

        cache.set(cache_key, product_ids, 3600)  # Cache for 1 hour
        return product_ids

    def get_trending_products(self, limit=10, days=7, category_id=None):
        """
        Get trending products based on recent interactions
        """
        cache_key = f'trending_{limit}_{days}_{category_id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        cutoff_date = timezone.now() - timedelta(days=days)

        # Calculate weighted scores for products
        interactions = ProductInteraction.objects.filter(
            created_at__gte=cutoff_date
        ).values('product_id', 'interaction_type')

        product_scores = defaultdict(float)
        for interaction in interactions:
            weight = self.interaction_weights.get(interaction['interaction_type'], 1.0)
            product_scores[interaction['product_id']] += weight

        # Sort by score
        sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
        product_ids = [p[0] for p in sorted_products]

        # Filter by category if specified
        if category_id:
            products = Product.objects.filter(
                id__in=product_ids,
                category_id=category_id,
                is_active=True
            )
        else:
            products = Product.objects.filter(
                id__in=product_ids,
                is_active=True
            )

        # Preserve order from scoring
        id_order = {id: idx for idx, id in enumerate(product_ids)}
        products = sorted(products, key=lambda x: id_order.get(x.id, 999))

        result_ids = [p.id for p in products[:limit]]

        cache.set(cache_key, result_ids, 1800)  # Cache for 30 minutes
        return result_ids

    def get_personalized_recommendations(self, customer_id, limit=10, exclude_products=None):
        """
        Hybrid approach: Combine collaborative and content-based filtering
        """
        exclude_products = exclude_products or []

        # Get collaborative recommendations
        collab_recs = self.get_collaborative_recommendations(customer_id, limit * 2, exclude_products)

        # Get content-based recommendations from recent views
        recent_views = ProductInteraction.objects.filter(
            customer_id=customer_id,
            interaction_type='view'
        ).order_by('-created_at').values_list('product_id', flat=True)[:5]

        content_recs = []
        for product_id in recent_views:
            content_recs.extend(self.get_content_based_recommendations(product_id, 5))

        # Combine and deduplicate
        all_recs = list(dict.fromkeys(collab_recs + content_recs))

        # If still not enough, add trending products
        if len(all_recs) < limit:
            trending = self.get_trending_products(limit * 2)
            all_recs.extend([p for p in trending if p not in all_recs and p not in exclude_products])

        return all_recs[:limit]

    def get_frequently_bought_together(self, product_id, limit=5):
        """
        Get products frequently bought together with this product
        """
        cache_key = f'fbt_{product_id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from orders.models import OrderItem

        # Get orders containing this product
        orders_with_product = OrderItem.objects.filter(
            product_id=product_id,
            order__status='delivered'
        ).values_list('order_id', flat=True)

        # Get other products in those orders
        other_products = OrderItem.objects.filter(
            order_id__in=orders_with_product
        ).exclude(
            product_id=product_id
        ).values('product_id').annotate(
            frequency=Count('id')
        ).order_by('-frequency')[:limit]

        product_ids = [p['product_id'] for p in other_products]

        cache.set(cache_key, product_ids, 3600)  # Cache for 1 hour
        return product_ids


# ============================================================================
# INTERACTION TRACKING VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List product interactions",
        description="Get product interaction history. Admin only.",
        tags=['Recommendations'],
    ),
)
class ProductInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing product interactions.

    Admin can view all interactions for analytics.
    """
    queryset = ProductInteraction.objects.select_related('customer', 'product').all()
    serializer_class = ProductInteractionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by customer
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        # Filter by interaction type
        interaction_type = self.request.query_params.get('type')
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)

        return queryset


# ============================================================================
# RECOMMENDATION VIEWS
# ============================================================================

@extend_schema(
    summary="Track product interaction",
    description="Track user interaction with a product (view, cart, purchase, etc.)",
    request=TrackInteractionSerializer,
    responses={201: ProductInteractionSerializer},
    examples=[
        OpenApiExample(
            'Track Product View',
            value={
                'product_id': 123,
                'interaction_type': 'view',
                'source': 'homepage',
                'duration_seconds': 45
            },
            request_only=True,
        ),
    ],
    tags=['Recommendations'],
)
class TrackInteractionView(views.APIView):
    """
    Track product interactions for recommendation engine
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Track interaction"""
        serializer = TrackInteractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        interaction_type = serializer.validated_data['interaction_type']

        # Get or create session
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key

        # Create interaction
        interaction = ProductInteraction.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            product_id=product_id,
            interaction_type=interaction_type,
            source=serializer.validated_data.get('source', ''),
            search_query=serializer.validated_data.get('search_query', ''),
            referrer_url=serializer.validated_data.get('referrer_url', ''),
            duration_seconds=serializer.validated_data.get('duration_seconds'),
            position=serializer.validated_data.get('position')
        )

        # Update product view count for 'view' interactions
        if interaction_type == 'view':
            Product.objects.filter(id=product_id).update(view_count=F('view_count') + 1)

        logger.info(f"Tracked {interaction_type} interaction for product {product_id}")

        response_serializer = ProductInteractionSerializer(interaction)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Get product recommendations",
    description="Get personalized product recommendations based on various algorithms",
    request=RecommendationRequestSerializer,
    responses={200: RecommendationResponseSerializer},
    tags=['Recommendations'],
)
class GetRecommendationsView(views.APIView):
    """
    Get product recommendations using AI algorithms
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Get recommendations"""
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recommendation_type = serializer.validated_data['recommendation_type']
        product_id = serializer.validated_data.get('product_id')
        limit = serializer.validated_data['limit']
        exclude_products = serializer.validated_data.get('exclude_products', [])

        engine = RecommendationEngine()

        # Get recommendations based on type
        if recommendation_type == 'collaborative':
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Collaborative recommendations require authentication'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            product_ids = engine.get_collaborative_recommendations(
                request.user.id, limit, exclude_products
            )

        elif recommendation_type == 'content_based':
            if not product_id:
                return Response(
                    {'error': 'product_id is required for content-based recommendations'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product_ids = engine.get_content_based_recommendations(product_id, limit)

        elif recommendation_type == 'trending':
            product_ids = engine.get_trending_products(limit)

        elif recommendation_type == 'personalized':
            if request.user.is_authenticated:
                product_ids = engine.get_personalized_recommendations(
                    request.user.id, limit, exclude_products
                )
            else:
                # For anonymous users, show trending products
                product_ids = engine.get_trending_products(limit)

        else:
            return Response(
                {'error': 'Invalid recommendation type'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get products
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).select_related('category', 'brand')

        # Preserve order from recommendation engine
        id_order = {id: idx for idx, id in enumerate(product_ids)}
        products = sorted(products, key=lambda x: id_order.get(x.id, 999))

        # Log recommendation
        session_id = request.session.session_key or ''
        RecommendationLog.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            recommendation_type=recommendation_type,
            recommended_products=[p.id for p in products],
            source_product_id=product_id,
            page_type=request.data.get('page_type', 'unknown')
        )

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        response_data = {
            'recommendation_type': recommendation_type,
            'products': product_serializer.data,
            'total_count': len(products),
            'source_product_id': product_id
        }

        return Response(response_data)


@extend_schema(
    summary="Get similar products",
    description="Get products similar to a specific product",
    request=SimilarProductsRequestSerializer,
    responses={200: ProductListSerializer(many=True)},
    tags=['Recommendations'],
)
class SimilarProductsView(views.APIView):
    """
    Get similar products using content-based filtering
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Get similar products"""
        serializer = SimilarProductsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        limit = serializer.validated_data['limit']

        engine = RecommendationEngine()
        product_ids = engine.get_content_based_recommendations(product_id, limit)

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).select_related('category', 'brand')

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        return Response(product_serializer.data)


@extend_schema(
    summary="Get trending products",
    description="Get currently trending products",
    request=TrendingProductsRequestSerializer,
    responses={200: ProductListSerializer(many=True)},
    tags=['Recommendations'],
)
class TrendingProductsView(views.APIView):
    """
    Get trending products based on recent activity
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Get trending products"""
        serializer = TrendingProductsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = serializer.validated_data['days']
        limit = serializer.validated_data['limit']
        category_id = serializer.validated_data.get('category_id')

        engine = RecommendationEngine()
        product_ids = engine.get_trending_products(limit, days, category_id)

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).select_related('category', 'brand')

        # Preserve order
        id_order = {id: idx for idx, id in enumerate(product_ids)}
        products = sorted(products, key=lambda x: id_order.get(x.id, 999))

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        return Response(product_serializer.data)


@extend_schema(
    summary="Get personalized recommendations",
    description="Get personalized recommendations for the current user",
    request=PersonalizedRecommendationsRequestSerializer,
    responses={200: ProductListSerializer(many=True)},
    tags=['Recommendations'],
)
class PersonalizedRecommendationsView(views.APIView):
    """
    Get personalized recommendations for authenticated users
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Get personalized recommendations"""
        serializer = PersonalizedRecommendationsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        limit = serializer.validated_data['limit']
        exclude_products = serializer.validated_data.get('exclude_products', [])
        page_type = serializer.validated_data['page_type']

        engine = RecommendationEngine()
        product_ids = engine.get_personalized_recommendations(
            request.user.id, limit, exclude_products
        )

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).select_related('category', 'brand')

        # Preserve order
        id_order = {id: idx for idx, id in enumerate(product_ids)}
        products = sorted(products, key=lambda x: id_order.get(x.id, 999))

        # Log recommendation
        session_id = request.session.session_key or ''
        RecommendationLog.objects.create(
            customer=request.user,
            session_id=session_id,
            recommendation_type='personalized',
            recommended_products=[p.id for p in products],
            page_type=page_type
        )

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        return Response(product_serializer.data)


@extend_schema(
    summary="Get frequently bought together",
    description="Get products frequently purchased together with a specific product",
    request=FrequentlyBoughtTogetherSerializer,
    responses={200: ProductListSerializer(many=True)},
    tags=['Recommendations'],
)
class FrequentlyBoughtTogetherView(views.APIView):
    """
    Get products frequently bought together
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Get frequently bought together products"""
        serializer = FrequentlyBoughtTogetherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        limit = serializer.validated_data['limit']

        engine = RecommendationEngine()
        product_ids = engine.get_frequently_bought_together(product_id, limit)

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).select_related('category', 'brand')

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        return Response(product_serializer.data)


@extend_schema(
    summary="Get recently viewed products",
    description="Get user's recently viewed products",
    request=RecentlyViewedSerializer,
    responses={200: ProductListSerializer(many=True)},
    tags=['Recommendations'],
)
class RecentlyViewedView(views.APIView):
    """
    Get recently viewed products for current user
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Get recently viewed products"""
        serializer = RecentlyViewedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        limit = serializer.validated_data['limit']
        exclude_products = serializer.validated_data.get('exclude_products', [])

        # Get recent views
        recent_product_ids = ProductInteraction.objects.filter(
            customer=request.user,
            interaction_type='view'
        ).exclude(
            product_id__in=exclude_products
        ).order_by('-created_at').values_list('product_id', flat=True).distinct()[:limit]

        products = Product.objects.filter(
            id__in=recent_product_ids,
            is_active=True
        ).select_related('category', 'brand')

        # Preserve order
        id_order = {id: idx for idx, id in enumerate(recent_product_ids)}
        products = sorted(products, key=lambda x: id_order.get(x.id, 999))

        product_serializer = ProductListSerializer(products, many=True, context={'request': request})

        return Response(product_serializer.data)


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

@extend_schema(
    summary="Get customer behavior analysis",
    description="Analyze customer behavior and preferences. Admin only.",
    request=CustomerBehaviorSerializer,
    responses={200: CustomerBehaviorResponseSerializer},
    tags=['Recommendations'],
)
class CustomerBehaviorView(views.APIView):
    """
    Analyze customer behavior for personalization
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Get customer behavior analysis"""
        serializer = CustomerBehaviorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id = serializer.validated_data['customer_id']
        days = serializer.validated_data['days']

        cutoff_date = timezone.now() - timedelta(days=days)

        # Get interactions
        interactions = ProductInteraction.objects.filter(
            customer_id=customer_id,
            created_at__gte=cutoff_date
        )

        # Count by type
        total_interactions = interactions.count()
        views = interactions.filter(interaction_type='view').count()
        cart_adds = interactions.filter(interaction_type='cart').count()
        purchases = interactions.filter(interaction_type='purchase').count()
        wishlist_adds = interactions.filter(interaction_type='wishlist').count()

        # Most viewed categories
        category_views = interactions.filter(
            interaction_type='view'
        ).values(
            'product__category__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        most_viewed_categories = [
            {'name': item['product__category__name'], 'count': item['count']}
            for item in category_views
        ]

        # Favorite brands
        brand_interactions = interactions.values(
            'product__brand__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        favorite_brands = [
            {'name': item['product__brand__name'], 'count': item['count']}
            for item in brand_interactions
        ]

        # Average session duration
        avg_duration = interactions.filter(
            duration_seconds__isnull=False
        ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0

        # Conversion rate
        conversion_rate = (purchases / views * 100) if views > 0 else 0

        response_data = {
            'total_interactions': total_interactions,
            'views': views,
            'cart_adds': cart_adds,
            'purchases': purchases,
            'wishlist_adds': wishlist_adds,
            'most_viewed_categories': most_viewed_categories,
            'favorite_brands': favorite_brands,
            'average_session_duration': float(avg_duration),
            'conversion_rate': float(conversion_rate)
        }

        response_serializer = CustomerBehaviorResponseSerializer(response_data)
        return Response(response_serializer.data)


@extend_schema(
    summary="Get product popularity metrics",
    description="Get popularity metrics for products. Admin only.",
    parameters=[
        OpenApiParameter(name='days', type=OpenApiTypes.INT, description='Number of days to analyze'),
    ],
    responses={200: ProductPopularitySerializer(many=True)},
    tags=['Recommendations'],
)
class ProductPopularityView(views.APIView):
    """
    Get product popularity metrics
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get product popularity"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        # Get interaction counts per product
        products = Product.objects.filter(is_active=True)

        results = []
        for product in products[:50]:  # Limit to top 50 for performance
            interactions = ProductInteraction.objects.filter(
                product=product,
                created_at__gte=cutoff_date
            )

            view_count = interactions.filter(interaction_type='view').count()
            cart_count = interactions.filter(interaction_type='cart').count()
            purchase_count = interactions.filter(interaction_type='purchase').count()
            wishlist_count = interactions.filter(interaction_type='wishlist').count()

            conversion_rate = (purchase_count / view_count * 100) if view_count > 0 else 0

            # Calculate popularity score
            popularity_score = (
                view_count * 1 +
                cart_count * 3 +
                purchase_count * 5 +
                wishlist_count * 2
            )

            results.append({
                'product_id': product.id,
                'view_count': view_count,
                'cart_count': cart_count,
                'purchase_count': purchase_count,
                'wishlist_count': wishlist_count,
                'conversion_rate': float(conversion_rate),
                'popularity_score': float(popularity_score)
            })

        # Sort by popularity score
        results.sort(key=lambda x: x['popularity_score'], reverse=True)

        serializer = ProductPopularitySerializer(results, many=True)
        return Response(serializer.data)


@extend_schema(
    summary="Get recommendation performance",
    description="Get performance metrics for the recommendation engine. Admin only.",
    parameters=[
        OpenApiParameter(name='days', type=OpenApiTypes.INT, description='Number of days to analyze'),
    ],
    responses={200: RecommendationPerformanceSerializer},
    tags=['Recommendations'],
)
class RecommendationPerformanceView(views.APIView):
    """
    Get recommendation engine performance metrics
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get recommendation performance"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        logs = RecommendationLog.objects.filter(created_at__gte=cutoff_date)

        total_shown = logs.count()
        total_clicks = sum(len(log.clicked_products) for log in logs)
        total_conversions = logs.filter(conversion=True).count()

        click_through_rate = (total_clicks / (total_shown * 10) * 100) if total_shown > 0 else 0
        conversion_rate = (total_conversions / total_shown * 100) if total_shown > 0 else 0

        # Performance by type
        performance_by_type = {}
        for rec_type in ['collaborative', 'content_based', 'trending', 'personalized']:
            type_logs = logs.filter(recommendation_type=rec_type)
            type_count = type_logs.count()
            type_clicks = sum(len(log.clicked_products) for log in type_logs)
            type_conversions = type_logs.filter(conversion=True).count()

            performance_by_type[rec_type] = {
                'shown': type_count,
                'clicks': type_clicks,
                'conversions': type_conversions,
                'ctr': (type_clicks / (type_count * 10) * 100) if type_count > 0 else 0
            }

        response_data = {
            'total_recommendations_shown': total_shown,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'click_through_rate': float(click_through_rate),
            'conversion_rate': float(conversion_rate),
            'performance_by_type': performance_by_type,
            'top_performing_recommendations': []
        }

        serializer = RecommendationPerformanceSerializer(response_data)
        return Response(serializer.data)
