"""
Product Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.db.models import Q, Avg, Count, F
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Category, Brand, Product, ProductImage, ProductVariant, Tag, ProductReview
from .serializers import (
    CategorySerializer, CategoryListSerializer, CategoryTreeSerializer,
    BrandSerializer, BrandListSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    ProductImageSerializer, ProductVariantSerializer,
    TagSerializer,
    ProductReviewSerializer, ProductReviewCreateSerializer
)
from .filters import ProductFilter, ProductReviewFilter
from api.permissions import IsVerified, CanManageProducts, StaffOrOwnerPermission


# ============================================================================
# CATEGORY VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all categories",
        description="Retrieve a list of all active categories with optional filtering",
        parameters=[
            OpenApiParameter(
                name='parent',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by parent category ID (use 0 for root categories)',
            ),
            OpenApiParameter(
                name='is_featured',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter featured categories',
            ),
            OpenApiParameter(
                name='show_in_menu',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter categories shown in menu',
            ),
        ],
        tags=['Categories'],
    ),
    retrieve=extend_schema(
        summary="Get category details",
        description="Retrieve detailed information about a specific category",
        tags=['Categories'],
    ),
    create=extend_schema(
        summary="Create a new category",
        description="Create a new product category. Requires staff permissions.",
        tags=['Categories'],
    ),
    update=extend_schema(
        summary="Update a category",
        description="Update a category. Requires staff permissions.",
        tags=['Categories'],
    ),
    partial_update=extend_schema(
        summary="Partially update a category",
        description="Update specific fields of a category. Requires staff permissions.",
        tags=['Categories'],
    ),
    destroy=extend_schema(
        summary="Delete a category",
        description="Delete a category. Requires staff permissions.",
        tags=['Categories'],
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product categories.

    Supports hierarchical categories with parent-child relationships.
    """
    queryset = Category.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent', 'is_featured', 'show_in_menu']
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'name', 'created_at']
    ordering = ['display_order', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        elif self.action == 'tree':
            return CategoryTreeSerializer
        return CategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageProducts()]
        return [IsAuthenticatedOrReadOnly()]

    @extend_schema(
        summary="Get category tree",
        description="Retrieve hierarchical category tree structure",
        tags=['Categories'],
    )
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories in tree structure"""
        cache_key = 'category_tree'
        tree = cache.get(cache_key)

        if not tree:
            # Get root categories (no parent)
            root_categories = Category.objects.filter(
                parent=None,
                is_active=True
            ).prefetch_related('children')

            serializer = self.get_serializer(root_categories, many=True)
            tree = serializer.data
            cache.set(cache_key, tree, 3600)  # Cache for 1 hour

        return Response(tree)

    @extend_schema(
        summary="Get featured categories",
        description="Retrieve list of featured categories",
        tags=['Categories'],
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured categories"""
        categories = self.queryset.filter(is_featured=True)
        serializer = CategoryListSerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get category products",
        description="Get all products in a specific category",
        parameters=[
            OpenApiParameter(name='include_children', type=OpenApiTypes.BOOL, description='Include products from subcategories'),
        ],
        tags=['Categories'],
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products for a category"""
        category = self.get_object()
        include_children = request.query_params.get('include_children', 'false').lower() == 'true'

        if include_children:
            # Get this category and all descendants
            categories = [category]
            categories.extend(category.children.all())
            products = Product.objects.filter(category__in=categories, is_active=True)
        else:
            products = category.products.filter(is_active=True)

        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


# ============================================================================
# BRAND VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all brands",
        description="Retrieve a list of all active brands",
        parameters=[
            OpenApiParameter(name='is_featured', type=OpenApiTypes.BOOL, description='Filter featured brands'),
        ],
        tags=['Brands'],
    ),
    retrieve=extend_schema(
        summary="Get brand details",
        description="Retrieve detailed information about a specific brand",
        tags=['Brands'],
    ),
    create=extend_schema(
        summary="Create a new brand",
        description="Create a new brand. Requires staff permissions.",
        tags=['Brands'],
    ),
    update=extend_schema(
        summary="Update a brand",
        description="Update a brand. Requires staff permissions.",
        tags=['Brands'],
    ),
    destroy=extend_schema(
        summary="Delete a brand",
        description="Delete a brand. Requires staff permissions.",
        tags=['Brands'],
    ),
)
class BrandViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product brands.
    """
    queryset = Brand.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return BrandListSerializer
        return BrandSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageProducts()]
        return [IsAuthenticatedOrReadOnly()]

    @extend_schema(
        summary="Get featured brands",
        description="Retrieve list of featured brands",
        tags=['Brands'],
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured brands"""
        brands = self.queryset.filter(is_featured=True)
        serializer = BrandListSerializer(brands, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get brand products",
        description="Get all products for a specific brand",
        tags=['Brands'],
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products for a brand"""
        brand = self.get_object()
        products = brand.products.filter(is_active=True)

        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


# ============================================================================
# PRODUCT VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all products",
        description="""
        Retrieve a paginated list of all active products with comprehensive filtering, search, and sorting options.

        ## Filtering:
        - By category, brand, tags
        - Price range (min_price, max_price)
        - Featured, new arrivals
        - In stock status

        ## Search:
        Search by product name, description, or SKU

        ## Sorting:
        Sort by name, price, created date, rating, sales count
        """,
        parameters=[
            OpenApiParameter(name='category', type=OpenApiTypes.INT, description='Filter by category ID'),
            OpenApiParameter(name='brand', type=OpenApiTypes.INT, description='Filter by brand ID'),
            OpenApiParameter(name='is_featured', type=OpenApiTypes.BOOL, description='Filter featured products'),
            OpenApiParameter(name='is_new', type=OpenApiTypes.BOOL, description='Filter new products'),
            OpenApiParameter(name='min_price', type=OpenApiTypes.DECIMAL, description='Minimum price'),
            OpenApiParameter(name='max_price', type=OpenApiTypes.DECIMAL, description='Maximum price'),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, description='Search by name, description, SKU'),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR, description='Order by: name, -name, final_price, -final_price, created_at, -created_at, rating_average, -rating_average'),
        ],
        tags=['Products'],
    ),
    retrieve=extend_schema(
        summary="Get product details",
        description="Retrieve detailed information about a specific product including variants, images, and reviews",
        tags=['Products'],
    ),
    create=extend_schema(
        summary="Create a new product",
        description="Create a new product. Requires staff permissions.",
        tags=['Products'],
    ),
    update=extend_schema(
        summary="Update a product",
        description="Update all fields of a product. Requires staff permissions.",
        tags=['Products'],
    ),
    partial_update=extend_schema(
        summary="Partially update a product",
        description="Update specific fields of a product. Requires staff permissions.",
        tags=['Products'],
    ),
    destroy=extend_schema(
        summary="Delete a product",
        description="Delete a product. Requires staff permissions.",
        tags=['Products'],
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing products.

    Supports comprehensive filtering, search, ordering, and custom actions
    for recommendations, tracking views, and managing variants/images.
    """
    queryset = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('tags', 'images', 'variants')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku', 'barcode']
    ordering_fields = ['name', 'regular_price', 'sale_price', 'created_at', 'rating_average', 'sales_count', 'view_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageProducts()]
        elif self.action in ['track_view']:
            return []  # Allow anonymous
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        """
        Optionally filter products with query parameters
        """
        queryset = super().get_queryset()

        # Filter by tags
        tags = self.request.query_params.get('tags')
        if tags:
            tag_ids = [int(tag_id) for tag_id in tags.split(',')]
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to track view count"""
        instance = self.get_object()

        # Increment view count asynchronously (in production, use Celery)
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="Get featured products",
        description="Retrieve list of featured products",
        tags=['Products'],
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        products = self.queryset.filter(is_featured=True)[:20]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get new arrivals",
        description="Retrieve recently added products",
        parameters=[
            OpenApiParameter(name='days', type=OpenApiTypes.INT, description='Number of days (default: 30)'),
        ],
        tags=['Products'],
    )
    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        """Get new arrival products"""
        from django.utils import timezone
        from datetime import timedelta

        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        products = self.queryset.filter(created_at__gte=cutoff_date).order_by('-created_at')[:20]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get best sellers",
        description="Retrieve products with highest sales count",
        tags=['Products'],
    )
    @action(detail=False, methods=['get'])
    def best_sellers(self, request):
        """Get best-selling products"""
        products = self.queryset.filter(sales_count__gt=0).order_by('-sales_count')[:20]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get top rated products",
        description="Retrieve products with highest ratings",
        tags=['Products'],
    )
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Get top-rated products"""
        products = self.queryset.filter(
            rating_average__gte=4.0,
            rating_count__gte=5
        ).order_by('-rating_average', '-rating_count')[:20]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get product recommendations",
        description="Get recommended products based on this product (similar products)",
        tags=['Products'],
    )
    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get recommended products based on current product"""
        product = self.get_object()

        # Try to get from cache first
        cache_key = f'product_recommendations_{product.id}'
        recommended_ids = cache.get(cache_key)

        if not recommended_ids:
            # Simple recommendation: same category and brand
            recommended = Product.objects.filter(
                category=product.category,
                is_active=True
            ).exclude(id=product.id).order_by('-rating_average')[:10]

            recommended_ids = list(recommended.values_list('id', flat=True))
            cache.set(cache_key, recommended_ids, 3600)  # Cache for 1 hour

        products = Product.objects.filter(id__in=recommended_ids)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Track product view",
        description="Track a product view for analytics and recommendations",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'source': {'type': 'string', 'example': 'homepage'},
                    'duration_seconds': {'type': 'integer', 'example': 30},
                },
            }
        },
        tags=['Products'],
    )
    @action(detail=True, methods=['post'])
    def track_view(self, request, pk=None):
        """Track product view for recommendations"""
        product = self.get_object()

        # Create product interaction (for recommendation engine)
        from recommendations.models import ProductInteraction

        ProductInteraction.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key or 'anonymous',
            product=product,
            interaction_type='view',
            source=request.data.get('source', ''),
            duration_seconds=request.data.get('duration_seconds')
        )

        return Response({'status': 'tracked'})

    @extend_schema(
        summary="Get related products",
        description="Get products that are marked as related to this product",
        tags=['Products'],
    )
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """Get related products"""
        product = self.get_object()
        related = product.related_products.filter(is_active=True)
        serializer = ProductListSerializer(related, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get upsell products",
        description="Get upsell products (higher-value alternatives)",
        tags=['Products'],
    )
    @action(detail=True, methods=['get'])
    def upsells(self, request, pk=None):
        """Get upsell products"""
        product = self.get_object()
        upsells = product.upsell_products.filter(is_active=True)
        serializer = ProductListSerializer(upsells, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get cross-sell products",
        description="Get cross-sell products (complementary products)",
        tags=['Products'],
    )
    @action(detail=True, methods=['get'])
    def cross_sells(self, request, pk=None):
        """Get cross-sell products"""
        product = self.get_object()
        cross_sells = product.cross_sell_products.filter(is_active=True)
        serializer = ProductListSerializer(cross_sells, many=True, context={'request': request})
        return Response(serializer.data)


# ============================================================================
# PRODUCT VARIANT VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List product variants",
        description="Retrieve all variants for a specific product",
        tags=['Products'],
    ),
    create=extend_schema(
        summary="Create product variant",
        description="Create a new variant for a product. Requires staff permissions.",
        tags=['Products'],
    ),
    update=extend_schema(
        summary="Update product variant",
        description="Update a product variant. Requires staff permissions.",
        tags=['Products'],
    ),
    destroy=extend_schema(
        summary="Delete product variant",
        description="Delete a product variant. Requires staff permissions.",
        tags=['Products'],
    ),
)
class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product variants.
    """
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageProducts()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        """Filter variants by product if product_id provided"""
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


# ============================================================================
# PRODUCT IMAGE VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List product images",
        description="Retrieve all images for a specific product",
        tags=['Products'],
    ),
    create=extend_schema(
        summary="Upload product image",
        description="Upload a new image for a product. Requires staff permissions.",
        tags=['Products'],
    ),
    update=extend_schema(
        summary="Update product image",
        description="Update product image details. Requires staff permissions.",
        tags=['Products'],
    ),
    destroy=extend_schema(
        summary="Delete product image",
        description="Delete a product image. Requires staff permissions.",
        tags=['Products'],
    ),
)
class ProductImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product images.
    """
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageProducts()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        """Filter images by product if product_id provided"""
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset.order_by('order', 'id')


# ============================================================================
# TAG VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all tags",
        description="Retrieve a list of all product tags",
        tags=['Products'],
    ),
    retrieve=extend_schema(
        summary="Get tag details",
        description="Retrieve detailed information about a specific tag",
        tags=['Products'],
    ),
    create=extend_schema(
        summary="Create a new tag",
        description="Create a new product tag. Requires staff permissions.",
        tags=['Products'],
    ),
    destroy=extend_schema(
        summary="Delete a tag",
        description="Delete a product tag. Requires staff permissions.",
        tags=['Products'],
    ),
)
class TagViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [CanManageProducts()]
        return [IsAuthenticatedOrReadOnly()]

    @extend_schema(
        summary="Get products with tag",
        description="Get all products tagged with this tag",
        tags=['Products'],
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products for a tag"""
        tag = self.get_object()
        products = tag.products.filter(is_active=True)

        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


# ============================================================================
# PRODUCT REVIEW VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List product reviews",
        description="Retrieve all reviews with filtering options",
        parameters=[
            OpenApiParameter(name='product', type=OpenApiTypes.INT, description='Filter by product ID'),
            OpenApiParameter(name='customer', type=OpenApiTypes.INT, description='Filter by customer ID'),
            OpenApiParameter(name='rating', type=OpenApiTypes.INT, description='Filter by rating (1-5)'),
            OpenApiParameter(name='is_verified_purchase', type=OpenApiTypes.BOOL, description='Filter verified purchases'),
            OpenApiParameter(name='is_approved', type=OpenApiTypes.BOOL, description='Filter approved reviews'),
        ],
        tags=['Products'],
    ),
    retrieve=extend_schema(
        summary="Get review details",
        description="Retrieve detailed information about a specific review",
        tags=['Products'],
    ),
    create=extend_schema(
        summary="Create a product review",
        description="Submit a review for a product. Requires authentication.",
        tags=['Products'],
    ),
    update=extend_schema(
        summary="Update your review",
        description="Update your own product review",
        tags=['Products'],
    ),
    destroy=extend_schema(
        summary="Delete your review",
        description="Delete your own product review",
        tags=['Products'],
    ),
)
class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product reviews.

    Customers can create, update, and delete their own reviews.
    Staff can approve/reject reviews.
    """
    queryset = ProductReview.objects.filter(is_approved=True).select_related('product', 'customer')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductReviewFilter
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductReviewCreateSerializer
        return ProductReviewSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        """
        Unauthenticated users see only approved reviews.
        Staff see all reviews.
        Customers see approved reviews + their own.
        """
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            queryset = ProductReview.objects.all()
        elif self.request.user.is_authenticated:
            queryset = ProductReview.objects.filter(
                Q(is_approved=True) | Q(customer=self.request.user)
            )

        return queryset.select_related('product', 'customer')

    def perform_create(self, serializer):
        """Set customer and check if verified purchase"""
        product = serializer.validated_data['product']

        # Check if customer has purchased this product
        from orders.models import OrderItem
        is_verified_purchase = OrderItem.objects.filter(
            order__customer=self.request.user,
            order__status='delivered',
            product=product
        ).exists()

        serializer.save(
            customer=self.request.user,
            is_verified_purchase=is_verified_purchase
        )

        # Update product rating
        self.update_product_rating(product)

    def perform_update(self, serializer):
        """Only allow users to update their own reviews"""
        if serializer.instance.customer != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only update your own reviews")

        serializer.save()
        self.update_product_rating(serializer.instance.product)

    def perform_destroy(self, instance):
        """Only allow users to delete their own reviews"""
        if instance.customer != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own reviews")

        product = instance.product
        instance.delete()
        self.update_product_rating(product)

    @staticmethod
    def update_product_rating(product):
        """Update product's average rating and count"""
        stats = ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )

        product.rating_average = stats['avg_rating'] or 0
        product.rating_count = stats['total_reviews'] or 0
        product.save(update_fields=['rating_average', 'rating_count'])

    @extend_schema(
        summary="Mark review as helpful",
        description="Mark a review as helpful",
        tags=['Products'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_helpful(self, request, pk=None):
        """Mark review as helpful"""
        review = self.get_object()
        review.helpful_count = F('helpful_count') + 1
        review.save(update_fields=['helpful_count'])
        review.refresh_from_db()

        return Response({
            'message': 'Review marked as helpful',
            'helpful_count': review.helpful_count
        })

    @extend_schema(
        summary="Mark review as not helpful",
        description="Mark a review as not helpful",
        tags=['Products'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_not_helpful(self, request, pk=None):
        """Mark review as not helpful"""
        review = self.get_object()
        review.not_helpful_count = F('not_helpful_count') + 1
        review.save(update_fields=['not_helpful_count'])
        review.refresh_from_db()

        return Response({
            'message': 'Review marked as not helpful',
            'not_helpful_count': review.not_helpful_count
        })

    @extend_schema(
        summary="Approve review",
        description="Approve a pending review. Requires staff permissions.",
        tags=['Products'],
    )
    @action(detail=True, methods=['post'], permission_classes=[CanManageProducts])
    def approve(self, request, pk=None):
        """Approve a review (staff only)"""
        review = self.get_object()
        review.is_approved = True
        review.save(update_fields=['is_approved'])

        self.update_product_rating(review.product)

        return Response({'message': 'Review approved'})

    @extend_schema(
        summary="Reject review",
        description="Reject/hide a review. Requires staff permissions.",
        tags=['Products'],
    )
    @action(detail=True, methods=['post'], permission_classes=[CanManageProducts])
    def reject(self, request, pk=None):
        """Reject a review (staff only)"""
        review = self.get_object()
        review.is_approved = False
        review.save(update_fields=['is_approved'])

        self.update_product_rating(review.product)

        return Response({'message': 'Review rejected'})
