"""
Order Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging
from decimal import Decimal

from .models import Order, OrderItem, ShippingZone, ShippingMethod
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderUpdateStatusSerializer,
    OrderTrackingSerializer,
    OrderItemSerializer,
    ShippingMethodSerializer,
    ShippingZoneSerializer,
    CalculateShippingSerializer,
    OrderSummarySerializer,
)
from .filters import OrderFilter
from api.permissions import CanManageOrders, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


# ============================================================================
# ORDER VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List orders",
        description="Retrieve orders with comprehensive filtering. Customers see only their orders, staff see all.",
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, description='Filter by order status'),
            OpenApiParameter(name='payment_status', type=OpenApiTypes.STR, description='Filter by payment status'),
            OpenApiParameter(name='customer', type=OpenApiTypes.INT, description='Filter by customer ID (staff only)'),
        ],
        tags=['Orders'],
    ),
    retrieve=extend_schema(
        summary="Get order details",
        description="Retrieve detailed information about a specific order",
        tags=['Orders'],
    ),
    create=extend_schema(
        summary="Create new order",
        description="Create a new order from cart",
        request=OrderCreateSerializer,
        responses={201: OrderDetailSerializer},
        tags=['Orders'],
    ),
)
class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing orders.

    Customers can create and view their own orders.
    Staff can manage all orders.
    """
    queryset = Order.objects.select_related('customer').prefetch_related('items').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter
    http_method_names = ['get', 'post', 'patch']  # No full update or delete

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer

    def get_queryset(self):
        """Filter orders based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        # Return empty queryset for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()

        # Staff can see all orders
        if user.is_staff:
            return queryset

        # Customers can only see their own orders
        return queryset.filter(customer=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create order from cart"""
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Get cart
        from cart.models import Cart, CartItem
        try:
            cart = Cart.objects.get(customer=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart_items = cart.items.select_related('product', 'variant').all()

        if not cart_items:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate order totals
        subtotal = Decimal('0')
        for item in cart_items:
            price = item.unit_price or item.product.sale_price or item.product.regular_price
            if item.variant:
                price = item.variant.sale_price or item.variant.price
            subtotal += price * item.quantity

        # Get shipping, tax, discount from validated data
        shipping_amount = serializer.validated_data.get('shipping_amount', Decimal('0'))
        tax_amount = serializer.validated_data.get('tax_amount', Decimal('0'))
        discount_amount = serializer.validated_data.get('discount_amount', Decimal('0'))

        total_amount = subtotal + shipping_amount + tax_amount - discount_amount

        # Generate order number
        import random
        import string
        order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=6))}"

        # Create order
        order = Order.objects.create(
            order_number=order_number,
            customer=request.user,
            status='pending',
            payment_status='pending',
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            currency=serializer.validated_data.get('currency', 'USD'),
            payment_method=serializer.validated_data.get('payment_method', 'card'),
            shipping_method=serializer.validated_data.get('shipping_method', 'standard'),
            billing_address=serializer.validated_data.get('billing_address', {}),
            shipping_address=serializer.validated_data.get('shipping_address', {}),
            customer_notes=serializer.validated_data.get('customer_notes', ''),
            coupon_code=serializer.validated_data.get('coupon_code', ''),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        # Create order items from cart
        for cart_item in cart_items:
            price = cart_item.unit_price or cart_item.product.sale_price or cart_item.product.regular_price
            if cart_item.variant:
                price = cart_item.variant.sale_price or cart_item.variant.price

            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                variant_name=cart_item.variant.name if cart_item.variant else '',
                quantity=cart_item.quantity,
                unit_price=price,
                total_price=price * cart_item.quantity,
                tax_amount=Decimal('0'),  # Calculate if needed
                discount_amount=Decimal('0')
            )

            # Reserve inventory
            from inventory.models import InventoryItem
            inventory = InventoryItem.objects.filter(
                product=cart_item.product,
                variant=cart_item.variant
            ).first()

            if inventory:
                inventory.quantity_reserved += cart_item.quantity
                inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
                inventory.save()

        # Clear cart
        cart.items.all().delete()

        logger.info(f"Order created: {order.order_number} by user {request.user.id}")

        serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Update order status",
        description="Update order status. Staff only.",
        request=OrderUpdateStatusSerializer,
        responses={200: OrderDetailSerializer},
        tags=['Orders'],
    )
    @action(detail=True, methods=['patch'], permission_classes=[CanManageOrders])
    def update_status(self, request, pk=None):
        """Update order status (staff only)"""
        order = self.get_object()

        serializer = OrderUpdateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        # Validate status transition
        if order.status == 'cancelled' and new_status not in ['cancelled', 'refunded']:
            return Response(
                {'error': 'Cannot change status of cancelled order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = order.status
        order.status = new_status

        # Update related timestamps
        if new_status == 'shipped' and not order.shipped_at:
            order.shipped_at = timezone.now()
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = timezone.now()

        if notes:
            order.admin_notes = (order.admin_notes or '') + f"\n[{timezone.now()}] {notes}"

        order.save()

        logger.info(f"Order {order.order_number} status changed from {old_status} to {new_status}")

        serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Cancel order",
        description="Cancel an order. Customer can cancel pending orders, staff can cancel any order.",
        request={'application/json': {'type': 'object', 'properties': {'reason': {'type': 'string'}}}},
        tags=['Orders'],
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()

        # Check permissions
        if not request.user.is_staff and order.customer != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.status in ['delivered', 'cancelled', 'refunded']:
            return Response(
                {'error': f'Cannot cancel {order.status} order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Customer requested cancellation')

        with transaction.atomic():
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.admin_notes = (order.admin_notes or '') + f"\n[{timezone.now()}] Cancelled: {reason}"
            order.save()

            # Release reserved inventory
            for item in order.items.all():
                from inventory.models import InventoryItem
                inventory = InventoryItem.objects.filter(
                    product=item.product,
                    variant=item.variant
                ).first()

                if inventory:
                    inventory.quantity_reserved -= item.quantity
                    inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
                    inventory.save()

        logger.info(f"Order {order.order_number} cancelled by user {request.user.id}")

        return Response({
            'message': 'Order cancelled successfully',
            'order_number': order.order_number,
            'status': order.status
        })

    @extend_schema(
        summary="Track order",
        description="Get order tracking information",
        responses={200: OrderTrackingSerializer},
        tags=['Orders'],
    )
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Get order tracking information"""
        order = self.get_object()

        tracking_info = {
            'order_number': order.order_number,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'carrier': order.carrier,
            'estimated_delivery': order.estimated_delivery_date,
            'timeline': []
        }

        # Build timeline
        if order.created_at:
            tracking_info['timeline'].append({
                'status': 'pending',
                'timestamp': order.created_at,
                'message': 'Order placed'
            })

        if order.paid_at:
            tracking_info['timeline'].append({
                'status': 'paid',
                'timestamp': order.paid_at,
                'message': 'Payment confirmed'
            })

        if order.status == 'processing':
            tracking_info['timeline'].append({
                'status': 'processing',
                'timestamp': order.updated_at,
                'message': 'Order being processed'
            })

        if order.shipped_at:
            tracking_info['timeline'].append({
                'status': 'shipped',
                'timestamp': order.shipped_at,
                'message': f'Order shipped via {order.carrier or "courier"}'
            })

        if order.delivered_at:
            tracking_info['timeline'].append({
                'status': 'delivered',
                'timestamp': order.delivered_at,
                'message': 'Order delivered'
            })

        if order.cancelled_at:
            tracking_info['timeline'].append({
                'status': 'cancelled',
                'timestamp': order.cancelled_at,
                'message': 'Order cancelled'
            })

        serializer = OrderTrackingSerializer(tracking_info)
        return Response(serializer.data)

    @extend_schema(
        summary="Add tracking number",
        description="Add tracking number to order. Staff only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'tracking_number': {'type': 'string'},
                    'carrier': {'type': 'string'},
                },
                'required': ['tracking_number']
            }
        },
        tags=['Orders'],
    )
    @action(detail=True, methods=['post'], permission_classes=[CanManageOrders])
    def add_tracking(self, request, pk=None):
        """Add tracking number (staff only)"""
        order = self.get_object()

        tracking_number = request.data.get('tracking_number')
        carrier = request.data.get('carrier', '')

        if not tracking_number:
            return Response(
                {'error': 'Tracking number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.tracking_number = tracking_number
        order.carrier = carrier

        if order.status == 'processing':
            order.status = 'shipped'
            order.shipped_at = timezone.now()

        order.save()

        logger.info(f"Tracking added to order {order.order_number}: {tracking_number}")

        return Response({
            'message': 'Tracking information added',
            'tracking_number': tracking_number,
            'carrier': carrier
        })

    @extend_schema(
        summary="Get order invoice",
        description="Generate and retrieve order invoice",
        tags=['Orders'],
    )
    @action(detail=True, methods=['get'])
    def invoice(self, request, pk=None):
        """Get order invoice"""
        order = self.get_object()

        invoice_data = {
            'order_number': order.order_number,
            'invoice_number': f"INV-{order.order_number}",
            'date': order.created_at,
            'customer': {
                'name': order.customer.get_full_name() if order.customer else order.guest_email,
                'email': order.customer.email if order.customer else order.guest_email,
            },
            'billing_address': order.billing_address,
            'items': [],
            'subtotal': float(order.subtotal),
            'tax_amount': float(order.tax_amount),
            'shipping_amount': float(order.shipping_amount),
            'discount_amount': float(order.discount_amount),
            'total_amount': float(order.total_amount),
            'currency': order.currency,
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
        }

        # Add items
        for item in order.items.all():
            invoice_data['items'].append({
                'product_name': item.product_name,
                'sku': item.product_sku,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
            })

        return Response(invoice_data)

    @extend_schema(
        summary="Get order summary",
        description="Get order statistics summary for customer",
        responses={200: OrderSummarySerializer},
        tags=['Orders'],
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get order summary for current user"""
        user = request.user
        orders = Order.objects.filter(customer=user)

        summary = {
            'total_orders': orders.count(),
            'total_spent': float(orders.filter(
                payment_status='paid'
            ).aggregate(total=Sum('total_amount'))['total'] or 0),
            'pending_orders': orders.filter(status='pending').count(),
            'processing_orders': orders.filter(status='processing').count(),
            'shipped_orders': orders.filter(status='shipped').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
            'average_order_value': 0,
        }

        if summary['total_orders'] > 0:
            summary['average_order_value'] = summary['total_spent'] / summary['total_orders']

        serializer = OrderSummarySerializer(summary)
        return Response(serializer.data)

    @extend_schema(
        summary="Reorder",
        description="Create a new order from a previous order",
        tags=['Orders'],
    )
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Create new order from previous order"""
        old_order = self.get_object()

        # Get or create cart
        from cart.models import Cart, CartItem
        cart, created = Cart.objects.get_or_create(customer=request.user)

        # Clear existing cart items
        cart.items.all().delete()

        # Add items from old order to cart
        for item in old_order.items.all():
            # Check if product is still available
            if not item.product.is_active:
                continue

            # Get current price
            price = item.product.sale_price or item.product.regular_price
            if item.variant:
                price = item.variant.sale_price or item.variant.price

            CartItem.objects.create(
                cart=cart,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                unit_price=price
            )

        return Response({
            'message': 'Items added to cart from previous order',
            'items_added': old_order.items.count(),
            'cart_id': cart.id
        })

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================================
# SHIPPING VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List shipping zones",
        description="Retrieve all shipping zones",
        tags=['Shipping'],
    ),
    retrieve=extend_schema(
        summary="Get shipping zone details",
        description="Retrieve detailed information about a shipping zone",
        tags=['Shipping'],
    ),
)
class ShippingZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing shipping zones.
    """
    queryset = ShippingZone.objects.filter(is_active=True).prefetch_related('methods')
    serializer_class = ShippingZoneSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Calculate shipping cost",
        description="Calculate shipping cost for given parameters",
        request=CalculateShippingSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=['Shipping'],
    )
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate shipping cost"""
        serializer = CalculateShippingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        country = serializer.validated_data['country']
        subtotal = serializer.validated_data['subtotal']
        weight = serializer.validated_data.get('weight', 0)

        # Find shipping zone for country
        zone = ShippingZone.objects.filter(
            is_active=True,
            countries__contains=[country]
        ).first()

        if not zone:
            return Response({
                'available_methods': [],
                'message': 'No shipping methods available for this location'
            })

        # Get available shipping methods
        methods = zone.methods.filter(is_active=True)
        available_methods = []

        for method in methods:
            # Check minimum order amount
            if method.min_order_amount and subtotal < method.min_order_amount:
                continue

            # Calculate cost
            if method.is_free:
                cost = Decimal('0')
            else:
                cost = method.flat_rate or Decimal('0')

                # Add weight-based calculation if needed
                # cost += weight * method.rate_per_kg

            available_methods.append({
                'id': method.id,
                'name': method.name,
                'delivery_time': method.delivery_time,
                'cost': float(cost),
                'currency': 'USD',
                'is_free': method.is_free
            })

        return Response({
            'zone': zone.name,
            'available_methods': available_methods
        })


@extend_schema_view(
    list=extend_schema(
        summary="List shipping methods",
        description="Retrieve all shipping methods",
        parameters=[
            OpenApiParameter(name='zone', type=OpenApiTypes.INT, description='Filter by zone ID'),
        ],
        tags=['Shipping'],
    ),
)
class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing shipping methods.
    """
    queryset = ShippingMethod.objects.filter(is_active=True).select_related('zone')
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['zone']
