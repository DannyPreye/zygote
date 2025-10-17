"""
Customer Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Avg, Count
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Customer, CustomerGroup, Address
from .serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
    ChangePasswordSerializer,
    CustomerStatsSerializer,
    AddressSerializer,
    AddressCreateUpdateSerializer,
    CustomerGroupSerializer,
)
from .filters import CustomerFilter, AddressFilter
from api.permissions import IsOwnerOrAdmin, IsVerified


# ============================================================================
# CUSTOMER VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all customers",
        description="Retrieve a list of all customers with filtering options. Admin only.",
        parameters=[
            OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter(name='is_verified', type=OpenApiTypes.BOOL, description='Filter verified customers'),
            OpenApiParameter(name='is_vip', type=OpenApiTypes.BOOL, description='Filter VIP customers'),
            OpenApiParameter(name='loyalty_tier', type=OpenApiTypes.STR, description='Filter by loyalty tier'),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, description='Search by name, email, username'),
        ],
        tags=['Customers'],
    ),
    retrieve=extend_schema(
        summary="Get customer details",
        description="Retrieve detailed information about a specific customer",
        tags=['Customers'],
    ),
    update=extend_schema(
        summary="Update customer",
        description="Update customer information. Admin only.",
        tags=['Customers'],
    ),
    partial_update=extend_schema(
        summary="Partially update customer",
        description="Update specific customer fields. Admin only.",
        tags=['Customers'],
    ),
    destroy=extend_schema(
        summary="Delete customer",
        description="Delete a customer account. Admin only.",
        tags=['Customers'],
    ),
)
class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing customers.

    Admin: Full access to all customers
    Authenticated users: Can view their own profile only
    """
    queryset = Customer.objects.all().prefetch_related('addresses', 'customer_groups')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['date_joined', 'total_orders', 'total_spent', 'last_order_date']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomerProfileSerializer
        return CustomerDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'destroy']:
            return [IsAdminUser()]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Non-admin users can only see their own profile
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(id=user.id)

        return queryset

    @extend_schema(
        summary="Get current user profile",
        description="Retrieve the authenticated user's profile",
        tags=['Customers'],
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user's profile"""
        serializer = CustomerDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update current user profile",
        description="Update the authenticated user's profile",
        request=CustomerProfileSerializer,
        tags=['Customers'],
    )
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update current user's profile"""
        serializer = CustomerProfileSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Change password",
        description="Change the authenticated user's password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        tags=['Customers'],
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Set new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({
            'message': 'Password changed successfully',
            'detail': 'Please login again with your new password'
        })

    @extend_schema(
        summary="Get customer statistics",
        description="Get comprehensive statistics for a customer",
        responses={200: CustomerStatsSerializer},
        tags=['Customers'],
    )
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def stats(self, request, pk=None):
        """Get customer statistics"""
        customer = self.get_object()

        stats = {
            'total_orders': customer.total_orders,
            'total_spent': customer.total_spent,
            'average_order_value': customer.average_order_value,
            'last_order_date': customer.last_order_date,
            'loyalty_points': customer.loyalty_points,
            'loyalty_tier': customer.loyalty_tier,
        }

        serializer = CustomerStatsSerializer(stats)
        return Response(serializer.data)

    @extend_schema(
        summary="Get customer order history",
        description="Get all orders for a customer",
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, description='Filter by order status'),
        ],
        tags=['Customers'],
    )
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def orders(self, request, pk=None):
        """Get customer's order history"""
        customer = self.get_object()

        # Import here to avoid circular imports
        from orders.models import Order
        from orders.serializers import OrderListSerializer

        orders = Order.objects.filter(customer=customer)

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)

        orders = orders.order_by('-created_at')

        # Apply pagination
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = OrderListSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get customer wishlist",
        description="Get all items in customer's wishlist",
        tags=['Customers'],
    )
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def wishlist(self, request, pk=None):
        """Get customer's wishlist"""
        customer = self.get_object()

        # Import here to avoid circular imports
        from cart.models import Wishlist
        from cart.serializers import WishlistSerializer

        wishlist_items = Wishlist.objects.filter(customer=customer).select_related('product')
        serializer = WishlistSerializer(wishlist_items, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get customer reviews",
        description="Get all reviews written by a customer",
        tags=['Customers'],
    )
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrAdmin])
    def reviews(self, request, pk=None):
        """Get customer's product reviews"""
        customer = self.get_object()

        # Import here to avoid circular imports
        from products.models import ProductReview
        from products.serializers import ProductReviewSerializer

        reviews = ProductReview.objects.filter(customer=customer).select_related('product')

        # Apply pagination
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ProductReviewSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Verify customer account",
        description="Mark a customer account as verified. Admin only.",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify customer account (admin only)"""
        customer = self.get_object()
        customer.is_verified = True
        customer.save(update_fields=['is_verified'])

        return Response({
            'message': 'Customer account verified successfully',
            'customer_id': customer.id,
            'is_verified': customer.is_verified
        })

    @extend_schema(
        summary="Upgrade to VIP",
        description="Upgrade a customer to VIP status. Admin only.",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def make_vip(self, request, pk=None):
        """Make customer VIP (admin only)"""
        customer = self.get_object()
        customer.is_vip = True
        customer.save(update_fields=['is_vip'])

        return Response({
            'message': 'Customer upgraded to VIP successfully',
            'customer_id': customer.id,
            'is_vip': customer.is_vip
        })

    @extend_schema(
        summary="Update loyalty tier",
        description="Update customer's loyalty tier based on spending. Admin only.",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def update_loyalty_tier(self, request, pk=None):
        """Update customer loyalty tier based on spending"""
        customer = self.get_object()

        # Loyalty tier logic
        total_spent = float(customer.total_spent)

        if total_spent >= 10000:
            tier = 'platinum'
        elif total_spent >= 5000:
            tier = 'gold'
        elif total_spent >= 1000:
            tier = 'silver'
        else:
            tier = 'bronze'

        customer.loyalty_tier = tier
        customer.save(update_fields=['loyalty_tier'])

        return Response({
            'message': 'Loyalty tier updated successfully',
            'customer_id': customer.id,
            'loyalty_tier': customer.loyalty_tier,
            'total_spent': customer.total_spent
        })

    @extend_schema(
        summary="Add loyalty points",
        description="Add loyalty points to customer account. Admin only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'points': {'type': 'integer', 'example': 100},
                    'reason': {'type': 'string', 'example': 'Purchase reward'},
                },
                'required': ['points']
            }
        },
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def add_loyalty_points(self, request, pk=None):
        """Add loyalty points to customer"""
        customer = self.get_object()
        points = request.data.get('points', 0)
        reason = request.data.get('reason', 'Manual adjustment')

        if not isinstance(points, int) or points <= 0:
            return Response(
                {'error': 'Points must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.loyalty_points += points
        customer.save(update_fields=['loyalty_points'])

        return Response({
            'message': f'{points} loyalty points added successfully',
            'customer_id': customer.id,
            'new_balance': customer.loyalty_points,
            'reason': reason
        })

    @extend_schema(
        summary="Deactivate account",
        description="Deactivate customer account",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def deactivate(self, request, pk=None):
        """Deactivate customer account"""
        customer = self.get_object()
        customer.is_active = False
        customer.save(update_fields=['is_active'])

        return Response({
            'message': 'Account deactivated successfully',
            'customer_id': customer.id
        })

    @extend_schema(
        summary="Reactivate account",
        description="Reactivate a deactivated customer account. Admin only.",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reactivate(self, request, pk=None):
        """Reactivate customer account"""
        customer = self.get_object()
        customer.is_active = True
        customer.save(update_fields=['is_active'])

        return Response({
            'message': 'Account reactivated successfully',
            'customer_id': customer.id
        })


# ============================================================================
# ADDRESS VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List customer addresses",
        description="Retrieve all addresses for the authenticated customer",
        parameters=[
            OpenApiParameter(name='address_type', type=OpenApiTypes.STR, description='Filter by address type (billing/shipping)'),
        ],
        tags=['Customers'],
    ),
    retrieve=extend_schema(
        summary="Get address details",
        description="Retrieve details of a specific address",
        tags=['Customers'],
    ),
    create=extend_schema(
        summary="Create new address",
        description="Add a new address for the authenticated customer",
        tags=['Customers'],
    ),
    update=extend_schema(
        summary="Update address",
        description="Update an existing address",
        tags=['Customers'],
    ),
    partial_update=extend_schema(
        summary="Partially update address",
        description="Update specific fields of an address",
        tags=['Customers'],
    ),
    destroy=extend_schema(
        summary="Delete address",
        description="Delete an address",
        tags=['Customers'],
    ),
)
class AddressViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing customer addresses.

    Customers can only manage their own addresses.
    """
    queryset = Address.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AddressFilter
    ordering_fields = ['created_at', 'is_default']
    ordering = ['-is_default', '-created_at']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AddressCreateUpdateSerializer
        return AddressSerializer

    def get_queryset(self):
        """
        Users can only see their own addresses
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(customer=user)

        return queryset

    def perform_create(self, serializer):
        """Set customer to current user"""
        address = serializer.save(customer=self.request.user)

        # If this is set as default, unset other defaults
        if address.is_default:
            Address.objects.filter(
                customer=self.request.user,
                address_type=address.address_type
            ).exclude(id=address.id).update(is_default=False)

    def perform_update(self, serializer):
        """Handle default address logic"""
        address = serializer.save()

        # If this is set as default, unset other defaults
        if address.is_default:
            Address.objects.filter(
                customer=address.customer,
                address_type=address.address_type
            ).exclude(id=address.id).update(is_default=False)

    @extend_schema(
        summary="Set as default address",
        description="Set this address as the default for its type",
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set address as default"""
        address = self.get_object()

        # Unset other defaults of same type
        Address.objects.filter(
            customer=address.customer,
            address_type=address.address_type
        ).update(is_default=False)

        # Set this as default
        address.is_default = True
        address.save(update_fields=['is_default'])

        return Response({
            'message': 'Address set as default',
            'address_id': address.id
        })


# ============================================================================
# CUSTOMER GROUP VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List customer groups",
        description="Retrieve all customer groups/segments",
        tags=['Customers'],
    ),
    retrieve=extend_schema(
        summary="Get customer group details",
        description="Retrieve details of a specific customer group",
        tags=['Customers'],
    ),
    create=extend_schema(
        summary="Create customer group",
        description="Create a new customer group. Admin only.",
        tags=['Customers'],
    ),
    update=extend_schema(
        summary="Update customer group",
        description="Update a customer group. Admin only.",
        tags=['Customers'],
    ),
    destroy=extend_schema(
        summary="Delete customer group",
        description="Delete a customer group. Admin only.",
        tags=['Customers'],
    ),
)
class CustomerGroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing customer groups/segments.

    Admin only for create/update/delete.
    """
    queryset = CustomerGroup.objects.all()
    serializer_class = CustomerGroupSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Get group members",
        description="Get all customers in this group",
        tags=['Customers'],
    )
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get customers in this group"""
        group = self.get_object()
        customers = group.customers.all()

        # Apply pagination
        page = self.paginate_queryset(customers)
        if page is not None:
            serializer = CustomerListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = CustomerListSerializer(customers, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Add customer to group",
        description="Add a customer to this group. Admin only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'customer_id': {'type': 'integer', 'example': 123},
                },
                'required': ['customer_id']
            }
        },
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def add_member(self, request, pk=None):
        """Add customer to group"""
        group = self.get_object()
        customer_id = request.data.get('customer_id')

        try:
            customer = Customer.objects.get(id=customer_id)
            group.customers.add(customer)

            return Response({
                'message': 'Customer added to group successfully',
                'group': group.name,
                'customer': customer.get_full_name() or customer.username
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        summary="Remove customer from group",
        description="Remove a customer from this group. Admin only.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'customer_id': {'type': 'integer', 'example': 123},
                },
                'required': ['customer_id']
            }
        },
        tags=['Customers'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def remove_member(self, request, pk=None):
        """Remove customer from group"""
        group = self.get_object()
        customer_id = request.data.get('customer_id')

        try:
            customer = Customer.objects.get(id=customer_id)
            group.customers.remove(customer)

            return Response({
                'message': 'Customer removed from group successfully',
                'group': group.name,
                'customer': customer.get_full_name() or customer.username
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# CUSTOMER REGISTRATION VIEW
# ============================================================================

@extend_schema(
    summary="Register new customer",
    description="Create a new customer account",
    request=CustomerRegistrationSerializer,
    responses={
        201: CustomerDetailSerializer,
        400: OpenApiTypes.OBJECT,
    },
    tags=['Customers'],
)
class CustomerRegistrationView(generics.CreateAPIView):
    """
    API endpoint for customer registration.

    Public endpoint - no authentication required.
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()

        # Return customer details
        output_serializer = CustomerDetailSerializer(customer, context={'request': request})
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
