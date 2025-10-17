"""
Promotion and Coupon Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging
from decimal import Decimal

from .models import Promotion, Coupon, CouponUsage
from .serializers import (
    PromotionListSerializer,
    PromotionDetailSerializer,
    PromotionCreateUpdateSerializer,
    CouponSerializer,
    CouponCreateSerializer,
    ValidateCouponSerializer,
    CouponValidationResponseSerializer,
    CouponUsageSerializer,
    ApplyCouponSerializer,
    PromotionStatsSerializer,
)
from .filters import PromotionFilter, CouponFilter
from api.permissions import CanManagePromotions

logger = logging.getLogger(__name__)


# ============================================================================
# PROMOTION VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List promotions",
        description="Retrieve all promotions. Public endpoint shows only active promotions.",
        parameters=[
            OpenApiParameter(name='discount_type', type=OpenApiTypes.STR, description='Filter by discount type'),
            OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter(name='is_featured', type=OpenApiTypes.BOOL, description='Filter by featured status'),
        ],
        tags=['Promotions'],
    ),
    retrieve=extend_schema(
        summary="Get promotion details",
        description="Retrieve detailed information about a specific promotion",
        tags=['Promotions'],
    ),
    create=extend_schema(
        summary="Create promotion",
        description="Create a new promotion. Admin only.",
        request=PromotionCreateUpdateSerializer,
        responses={201: PromotionDetailSerializer},
        tags=['Promotions'],
    ),
    update=extend_schema(
        summary="Update promotion",
        description="Update a promotion. Admin only.",
        request=PromotionCreateUpdateSerializer,
        responses={200: PromotionDetailSerializer},
        tags=['Promotions'],
    ),
    partial_update=extend_schema(
        summary="Partially update promotion",
        description="Partially update a promotion. Admin only.",
        request=PromotionCreateUpdateSerializer,
        responses={200: PromotionDetailSerializer},
        tags=['Promotions'],
    ),
)
class PromotionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing promotions.

    Public users can view active promotions.
    Admin users can create, update, and delete promotions.
    """
    queryset = Promotion.objects.all().prefetch_related(
        'products', 'categories', 'brands', 'customer_groups'
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = PromotionFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PromotionCreateUpdateSerializer
        return PromotionDetailSerializer

    def get_permissions(self):
        """
        Public can view promotions, admin can manage
        """
        if self.action in ['list', 'retrieve', 'active', 'featured', 'applicable']:
            return [AllowAny()]
        return [CanManagePromotions()]

    def get_queryset(self):
        """Filter promotions based on permissions"""
        queryset = super().get_queryset()

        # Non-admin users only see active promotions
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )

        return queryset

    @extend_schema(
        summary="Get active promotions",
        description="Get all currently active promotions",
        tags=['Promotions'],
    )
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def active(self, request):
        """Get active promotions"""
        now = timezone.now()
        promotions = self.get_queryset().filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

        serializer = PromotionListSerializer(promotions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get featured promotions",
        description="Get featured promotions for homepage display",
        tags=['Promotions'],
    )
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def featured(self, request):
        """Get featured promotions"""
        now = timezone.now()
        promotions = self.get_queryset().filter(
            is_active=True,
            is_featured=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-priority')[:5]

        serializer = PromotionListSerializer(promotions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get applicable promotions",
        description="Get promotions applicable to specific products or cart",
        parameters=[
            OpenApiParameter(name='product_id', type=OpenApiTypes.INT, description='Product ID'),
            OpenApiParameter(name='category_id', type=OpenApiTypes.INT, description='Category ID'),
            OpenApiParameter(name='brand_id', type=OpenApiTypes.INT, description='Brand ID'),
        ],
        tags=['Promotions'],
    )
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def applicable(self, request):
        """Get promotions applicable to specific products or cart"""
        product_id = request.query_params.get('product_id')
        category_id = request.query_params.get('category_id')
        brand_id = request.query_params.get('brand_id')

        now = timezone.now()
        promotions = self.get_queryset().filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

        # Filter by applicability
        if product_id:
            promotions = promotions.filter(
                Q(apply_to='all') |
                Q(apply_to='specific_products', products__id=product_id)
            )

        if category_id:
            promotions = promotions.filter(
                Q(apply_to='all') |
                Q(apply_to='specific_categories', categories__id=category_id)
            )

        if brand_id:
            promotions = promotions.filter(
                Q(apply_to='all') |
                Q(apply_to='specific_brands', brands__id=brand_id)
            )

        promotions = promotions.distinct()

        serializer = PromotionListSerializer(promotions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Calculate discount",
        description="Calculate discount amount for a specific promotion and cart",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'cart_total': {'type': 'number'},
                    'cart_quantity': {'type': 'integer'},
                },
                'required': ['cart_total']
            }
        },
        responses={200: OpenApiTypes.OBJECT},
        tags=['Promotions'],
    )
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def calculate_discount(self, request, pk=None):
        """Calculate discount for promotion"""
        promotion = self.get_object()

        cart_total = Decimal(request.data.get('cart_total', 0))
        cart_quantity = int(request.data.get('cart_quantity', 0))

        # Check if promotion is active
        now = timezone.now()
        if not (promotion.is_active and promotion.start_date <= now <= promotion.end_date):
            return Response({
                'applicable': False,
                'message': 'Promotion is not currently active'
            })

        # Check minimum purchase amount
        if promotion.min_purchase_amount and cart_total < promotion.min_purchase_amount:
            return Response({
                'applicable': False,
                'message': f'Minimum purchase amount is {promotion.min_purchase_amount}'
            })

        # Check minimum quantity
        if promotion.min_quantity and cart_quantity < promotion.min_quantity:
            return Response({
                'applicable': False,
                'message': f'Minimum quantity is {promotion.min_quantity}'
            })

        # Check usage limits
        if promotion.max_uses and promotion.used_count >= promotion.max_uses:
            return Response({
                'applicable': False,
                'message': 'Promotion has reached maximum usage limit'
            })

        # Calculate discount
        discount_amount = Decimal('0')

        if promotion.discount_type == 'percentage':
            discount_amount = (cart_total * promotion.discount_value) / Decimal('100')
        elif promotion.discount_type == 'fixed':
            discount_amount = promotion.discount_value
        elif promotion.discount_type == 'free_shipping':
            # Return special flag for free shipping
            return Response({
                'applicable': True,
                'discount_type': 'free_shipping',
                'message': 'Free shipping applied'
            })

        # Ensure discount doesn't exceed cart total
        discount_amount = min(discount_amount, cart_total)

        return Response({
            'applicable': True,
            'discount_type': promotion.discount_type,
            'discount_value': float(promotion.discount_value),
            'discount_amount': float(discount_amount),
            'final_total': float(cart_total - discount_amount)
        })

    @extend_schema(
        summary="Get promotion statistics",
        description="Get usage statistics for a promotion. Admin only.",
        tags=['Promotions'],
    )
    @action(detail=True, methods=['get'], permission_classes=[CanManagePromotions])
    def statistics(self, request, pk=None):
        """Get promotion statistics"""
        promotion = self.get_object()

        # Get total discount given
        total_discount = CouponUsage.objects.filter(
            coupon__promotion=promotion
        ).aggregate(total=Sum('discount_amount'))['total'] or Decimal('0')

        # Get usage count by time period
        from datetime import timedelta
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)

        usage_7_days = CouponUsage.objects.filter(
            coupon__promotion=promotion,
            created_at__gte=last_7_days
        ).count()

        usage_30_days = CouponUsage.objects.filter(
            coupon__promotion=promotion,
            created_at__gte=last_30_days
        ).count()

        stats = {
            'promotion_id': promotion.id,
            'promotion_name': promotion.name,
            'total_uses': promotion.used_count,
            'max_uses': promotion.max_uses,
            'remaining_uses': promotion.max_uses - promotion.used_count if promotion.max_uses else None,
            'total_discount_given': float(total_discount),
            'uses_last_7_days': usage_7_days,
            'uses_last_30_days': usage_30_days,
            'active_coupons': promotion.coupons.filter(used=False).count(),
            'used_coupons': promotion.coupons.filter(used=True).count(),
        }

        return Response(stats)

    @extend_schema(
        summary="Activate/deactivate promotion",
        description="Toggle promotion active status. Admin only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'is_active': {'type': 'boolean'},
                },
                'required': ['is_active']
            }
        },
        tags=['Promotions'],
    )
    @action(detail=True, methods=['patch'], permission_classes=[CanManagePromotions])
    def toggle_active(self, request, pk=None):
        """Activate or deactivate promotion"""
        promotion = self.get_object()

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response(
                {'error': 'is_active field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        promotion.is_active = is_active
        promotion.save()

        logger.info(f"Promotion {promotion.id} {'activated' if is_active else 'deactivated'}")

        return Response({
            'message': f'Promotion {"activated" if is_active else "deactivated"}',
            'is_active': promotion.is_active
        })


# ============================================================================
# COUPON VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List coupons",
        description="List all coupons. Admin sees all, users see only their own.",
        parameters=[
            OpenApiParameter(name='promotion', type=OpenApiTypes.INT, description='Filter by promotion ID'),
            OpenApiParameter(name='is_valid', type=OpenApiTypes.BOOL, description='Filter by validity'),
        ],
        tags=['Coupons'],
    ),
    retrieve=extend_schema(
        summary="Get coupon details",
        description="Retrieve detailed information about a coupon",
        tags=['Coupons'],
    ),
    create=extend_schema(
        summary="Create coupon",
        description="Create a new coupon. Admin only.",
        request=CouponCreateSerializer,
        responses={201: CouponSerializer},
        tags=['Coupons'],
    ),
)
class CouponViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing coupons.

    Admin users can create and manage coupons.
    Regular users can view their assigned coupons.
    """
    queryset = Coupon.objects.select_related('promotion', 'customer', 'used_by').all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = CouponFilter
    http_method_names = ['get', 'post', 'delete']

    def get_serializer_class(self):
        if self.action == 'create':
            return CouponCreateSerializer
        return CouponSerializer

    def get_permissions(self):
        """
        Admin can manage coupons, users can view their own
        """
        if self.action in ['create', 'destroy', 'bulk_generate']:
            return [CanManagePromotions()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Filter coupons based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        # Staff can see all coupons
        if user.is_staff:
            return queryset

        # Regular users can only see their assigned coupons
        return queryset.filter(Q(customer=user) | Q(customer__isnull=True))

    @extend_schema(
        summary="Validate coupon code",
        description="Validate a coupon code and get discount information",
        request=ValidateCouponSerializer,
        responses={200: CouponValidationResponseSerializer},
        examples=[
            OpenApiExample(
                'Validate Coupon',
                value={
                    'code': 'SAVE20',
                    'cart_total': 100.00,
                    'cart_quantity': 3
                },
                request_only=True,
            ),
        ],
        tags=['Coupons'],
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def validate(self, request):
        """Validate coupon code"""
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code'].upper()
        cart_total = serializer.validated_data.get('cart_total', Decimal('0'))
        cart_quantity = serializer.validated_data.get('cart_quantity', 0)

        try:
            coupon = Coupon.objects.select_related('promotion').get(code=code)
        except Coupon.DoesNotExist:
            return Response({
                'is_valid': False,
                'message': 'Invalid coupon code'
            })

        # Check if promotion is active
        promotion = coupon.promotion
        now = timezone.now()

        if not promotion.is_active:
            return Response({
                'is_valid': False,
                'message': 'This promotion is no longer active'
            })

        if now < promotion.start_date:
            return Response({
                'is_valid': False,
                'message': 'This promotion has not started yet'
            })

        if now > promotion.end_date:
            return Response({
                'is_valid': False,
                'message': 'This promotion has expired'
            })

        # Check if coupon is used (for single-use coupons)
        if coupon.is_single_use and coupon.used:
            return Response({
                'is_valid': False,
                'message': 'This coupon has already been used'
            })

        # Check if customer-specific
        if coupon.customer and coupon.customer != request.user:
            return Response({
                'is_valid': False,
                'message': 'This coupon is not assigned to you'
            })

        # Check usage limits
        if promotion.max_uses and promotion.used_count >= promotion.max_uses:
            return Response({
                'is_valid': False,
                'message': 'This promotion has reached its usage limit'
            })

        # Check per-customer usage limit
        customer_usage = CouponUsage.objects.filter(
            coupon__promotion=promotion,
            customer=request.user
        ).count()

        if customer_usage >= promotion.max_uses_per_customer:
            return Response({
                'is_valid': False,
                'message': f'You have already used this promotion {promotion.max_uses_per_customer} time(s)'
            })

        # Check minimum purchase amount
        if promotion.min_purchase_amount and cart_total < promotion.min_purchase_amount:
            return Response({
                'is_valid': False,
                'message': f'Minimum purchase amount is {promotion.min_purchase_amount}',
                'min_purchase_amount': float(promotion.min_purchase_amount)
            })

        # Check minimum quantity
        if promotion.min_quantity and cart_quantity < promotion.min_quantity:
            return Response({
                'is_valid': False,
                'message': f'Minimum quantity is {promotion.min_quantity}'
            })

        # Calculate discount
        discount_amount = Decimal('0')

        if promotion.discount_type == 'percentage':
            discount_amount = (cart_total * promotion.discount_value) / Decimal('100')
        elif promotion.discount_type == 'fixed':
            discount_amount = min(promotion.discount_value, cart_total)
        elif promotion.discount_type == 'free_shipping':
            return Response({
                'is_valid': True,
                'message': 'Valid coupon - Free shipping',
                'discount_type': 'free_shipping'
            })

        return Response({
            'is_valid': True,
            'message': 'Valid coupon',
            'discount_type': promotion.discount_type,
            'discount_value': float(promotion.discount_value),
            'discount_amount': float(discount_amount)
        })

    @extend_schema(
        summary="Apply coupon to order",
        description="Apply a coupon code to an order",
        request=ApplyCouponSerializer,
        tags=['Coupons'],
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def apply(self, request):
        """Apply coupon to order"""
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['coupon_code']
        order_id = serializer.validated_data['order_id']

        # Get order
        from orders.models import Order
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if order already has a coupon
        if CouponUsage.objects.filter(order=order).exists():
            return Response(
                {'error': 'Order already has a coupon applied'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get coupon
        try:
            coupon = Coupon.objects.select_related('promotion').get(code=code)
        except Coupon.DoesNotExist:
            return Response(
                {'error': 'Invalid coupon code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        promotion = coupon.promotion

        # Validate coupon (reuse validation logic)
        validation_data = {
            'code': code,
            'cart_total': order.subtotal,
            'cart_quantity': order.items.count()
        }

        # Perform validation
        validation_serializer = ValidateCouponSerializer(data=validation_data)
        validation_serializer.is_valid(raise_exception=True)

        # Calculate discount
        discount_amount = Decimal('0')

        if promotion.discount_type == 'percentage':
            discount_amount = (order.subtotal * promotion.discount_value) / Decimal('100')
        elif promotion.discount_type == 'fixed':
            discount_amount = min(promotion.discount_value, order.subtotal)

        # Apply discount to order
        with transaction.atomic():
            order.discount_amount = discount_amount
            order.total_amount = order.subtotal + order.tax_amount + order.shipping_amount - discount_amount
            order.coupon_code = code
            order.save()

            # Create usage record
            CouponUsage.objects.create(
                coupon=coupon,
                customer=request.user,
                order=order,
                discount_amount=discount_amount
            )

            # Update counters
            promotion.used_count += 1
            promotion.save()

            if coupon.is_single_use:
                coupon.used = True
                coupon.used_at = timezone.now()
                coupon.used_by = request.user
                coupon.save()

        logger.info(f"Coupon {code} applied to order {order.order_number} by user {request.user.id}")

        return Response({
            'message': 'Coupon applied successfully',
            'discount_amount': float(discount_amount),
            'new_total': float(order.total_amount)
        })

    @extend_schema(
        summary="Bulk generate coupons",
        description="Generate multiple coupon codes for a promotion. Admin only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'promotion_id': {'type': 'integer'},
                    'count': {'type': 'integer'},
                    'prefix': {'type': 'string'},
                    'is_single_use': {'type': 'boolean'},
                },
                'required': ['promotion_id', 'count']
            }
        },
        tags=['Coupons'],
    )
    @action(detail=False, methods=['post'], permission_classes=[CanManagePromotions])
    def bulk_generate(self, request):
        """Bulk generate coupon codes"""
        promotion_id = request.data.get('promotion_id')
        count = request.data.get('count', 10)
        prefix = request.data.get('prefix', 'PROMO')
        is_single_use = request.data.get('is_single_use', True)

        if not promotion_id:
            return Response(
                {'error': 'promotion_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if count > 1000:
            return Response(
                {'error': 'Maximum 1000 coupons per request'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            promotion = Promotion.objects.get(id=promotion_id)
        except Promotion.DoesNotExist:
            return Response(
                {'error': 'Promotion not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate coupons
        import random
        import string

        coupons_created = []
        for i in range(count):
            # Generate unique code
            while True:
                code = f"{prefix}{'-' if prefix else ''}{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
                if not Coupon.objects.filter(code=code).exists():
                    break

            coupon = Coupon.objects.create(
                code=code,
                promotion=promotion,
                is_single_use=is_single_use
            )
            coupons_created.append(coupon.code)

        logger.info(f"Bulk generated {count} coupons for promotion {promotion.id}")

        return Response({
            'message': f'Successfully generated {count} coupons',
            'codes': coupons_created
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get coupon usage history",
        description="Get usage history for a coupon. Admin only.",
        tags=['Coupons'],
    )
    @action(detail=True, methods=['get'], permission_classes=[CanManagePromotions])
    def usage_history(self, request, pk=None):
        """Get coupon usage history"""
        coupon = self.get_object()

        usage_history = CouponUsage.objects.filter(coupon=coupon).select_related(
            'customer', 'order'
        ).order_by('-created_at')

        serializer = CouponUsageSerializer(usage_history, many=True)
        return Response(serializer.data)


# ============================================================================
# STATISTICS VIEW
# ============================================================================

@extend_schema(
    summary="Get promotion statistics",
    description="Get overall promotion and coupon statistics. Admin only.",
    responses={200: PromotionStatsSerializer},
    tags=['Promotions'],
)
class PromotionStatsView(views.APIView):
    """
    Get overall promotion statistics
    """
    permission_classes = [CanManagePromotions]

    def get(self, request):
        """Get promotion statistics"""
        now = timezone.now()

        # Total promotions
        total_promotions = Promotion.objects.count()

        # Active promotions
        active_promotions = Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count()

        # Total discounts given
        total_discounts = CouponUsage.objects.aggregate(
            total=Sum('discount_amount')
        )['total'] or Decimal('0')

        # Total coupons used
        total_coupons_used = CouponUsage.objects.count()

        # Most used promotion
        most_used = Promotion.objects.filter(
            used_count__gt=0
        ).order_by('-used_count').first()

        stats = {
            'total_promotions': total_promotions,
            'active_promotions': active_promotions,
            'total_discounts_given': float(total_discounts),
            'total_coupons_used': total_coupons_used,
            'most_used_promotion': most_used.name if most_used else 'None'
        }

        serializer = PromotionStatsSerializer(stats)
        return Response(serializer.data)
