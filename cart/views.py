"""
Cart & Wishlist Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Cart, CartItem, Wishlist, WishlistItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    WishlistSerializer,
    WishlistItemSerializer,
    WishlistCreateSerializer,
    AddToWishlistSerializer,
)
from api.permissions import IsOwnerOrAdmin


# ============================================================================
# CART VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Get current cart",
        description="Retrieve the current user's shopping cart or session cart",
        tags=['Cart'],
    ),
    retrieve=extend_schema(
        summary="Get cart details",
        description="Retrieve detailed cart information",
        tags=['Cart'],
    ),
)
class CartViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing shopping carts.

    Supports both authenticated users and anonymous sessions.
    Anonymous users get a session-based cart, authenticated users get a persistent cart.
    """
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Get cart for current user or session"""
        if self.request.user.is_authenticated:
            return Cart.objects.filter(customer=self.request.user)
        else:
            session_id = self.request.session.session_key
            if session_id:
                return Cart.objects.filter(session_id=session_id)
        return Cart.objects.none()

    def list(self, request):
        """Get current cart"""
        cart = self._get_or_create_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get specific cart by ID"""
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    def _get_or_create_cart(self):
        """Get or create cart for current user/session"""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                customer=self.request.user,
                defaults={
                    'ip_address': self._get_client_ip(),
                    'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:200]
                }
            )
        else:
            # Create session if doesn't exist
            if not self.request.session.session_key:
                self.request.session.create()

            session_id = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(
                session_id=session_id,
                customer=None,
                defaults={
                    'ip_address': self._get_client_ip(),
                    'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:200]
                }
            )

        return cart

    def _get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    @extend_schema(
        summary="Add item to cart",
        description="Add a product (with optional variant) to the shopping cart",
        request=AddToCartSerializer,
        responses={
            200: CartSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Add product to cart',
                value={
                    'product_id': 123,
                    'variant_id': 456,
                    'quantity': 2,
                    'personalization': {'engraving': 'Happy Birthday!'}
                },
                request_only=True,
            ),
        ],
        tags=['Cart'],
    )
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        variant_id = serializer.validated_data.get('variant_id')
        quantity = serializer.validated_data['quantity']
        personalization = serializer.validated_data.get('personalization', {})

        cart = self._get_or_create_cart()

        # Check inventory
        if not self._check_inventory(product_id, variant_id, quantity):
            return Response(
                {'error': 'Insufficient stock available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get product price
        from products.models import Product, ProductVariant
        product = Product.objects.get(id=product_id)

        unit_price = product.sale_price or product.regular_price
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id)
            unit_price = variant.sale_price or variant.price

        # Add or update cart item
        with transaction.atomic():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product_id=product_id,
                variant_id=variant_id,
                defaults={
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'personalization': personalization
                }
            )

            if not created:
                # Update existing item
                cart_item.quantity += quantity
                cart_item.unit_price = unit_price  # Update price
                cart_item.personalization = personalization
                cart_item.save()

            # Update cart timestamp
            cart.save()

        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)

    @extend_schema(
        summary="Update cart item quantity",
        description="Update the quantity of a cart item",
        request=UpdateCartItemSerializer,
        responses={200: CartSerializer},
        tags=['Cart'],
    )
    @action(detail=False, methods=['post'], url_path='update-item/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item quantity"""
        cart = self._get_or_create_cart()

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data['quantity']

        if quantity == 0:
            # Remove item if quantity is 0
            cart_item.delete()
        else:
            # Check inventory
            if not self._check_inventory(
                cart_item.product_id,
                cart_item.variant_id,
                quantity
            ):
                return Response(
                    {'error': 'Insufficient stock available'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = quantity
            cart_item.save()

        # Update cart timestamp
        cart.save()

        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)

    @extend_schema(
        summary="Remove item from cart",
        description="Remove a specific item from the shopping cart",
        responses={200: CartSerializer},
        tags=['Cart'],
    )
    @action(detail=False, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart"""
        cart = self._get_or_create_cart()

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update cart timestamp
        cart.save()

        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)

    @extend_schema(
        summary="Clear cart",
        description="Remove all items from the shopping cart",
        responses={200: OpenApiTypes.OBJECT},
        tags=['Cart'],
    )
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = self._get_or_create_cart()
        cart.items.all().delete()

        return Response({
            'message': 'Cart cleared successfully',
            'items_count': 0
        })

    @extend_schema(
        summary="Get cart totals",
        description="Calculate cart totals including subtotal, tax, shipping, and total",
        responses={200: OpenApiTypes.OBJECT},
        tags=['Cart'],
    )
    @action(detail=False, methods=['get'])
    def totals(self, request):
        """Get cart totals"""
        cart = self._get_or_create_cart()

        subtotal = 0
        items_count = 0

        for item in cart.items.select_related('product', 'variant'):
            price = item.unit_price or item.product.sale_price or item.product.regular_price
            if item.variant:
                price = item.variant.sale_price or item.variant.price

            subtotal += price * item.quantity
            items_count += item.quantity

        # Calculate tax (example: 10% tax rate)
        tax_rate = 0.10
        tax_amount = subtotal * tax_rate

        # Shipping (example: free shipping over $50)
        shipping_amount = 0 if subtotal >= 50 else 10

        total = subtotal + tax_amount + shipping_amount

        return Response({
            'items_count': items_count,
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'tax_rate': tax_rate,
            'shipping_amount': round(shipping_amount, 2),
            'total': round(total, 2),
            'currency': 'USD'
        })

    @extend_schema(
        summary="Merge carts",
        description="Merge anonymous session cart with authenticated user cart",
        responses={200: CartSerializer},
        tags=['Cart'],
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def merge(self, request):
        """Merge session cart with user cart after login"""
        session_id = request.session.session_key

        if not session_id:
            return Response(
                {'message': 'No session cart to merge'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session_cart = Cart.objects.get(session_id=session_id, customer=None)
        except Cart.DoesNotExist:
            return Response(
                {'message': 'No session cart found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get or create user cart
        user_cart, created = Cart.objects.get_or_create(customer=request.user)

        # Merge items
        with transaction.atomic():
            for session_item in session_cart.items.all():
                user_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=session_item.product,
                    variant=session_item.variant,
                    defaults={
                        'quantity': session_item.quantity,
                        'unit_price': session_item.unit_price,
                        'personalization': session_item.personalization
                    }
                )

                if not created:
                    # Increase quantity if item already exists
                    user_item.quantity += session_item.quantity
                    user_item.save()

            # Delete session cart
            session_cart.delete()

        # Return merged cart
        cart_serializer = CartSerializer(user_cart, context={'request': request})
        return Response(cart_serializer.data)

    @extend_schema(
        summary="Apply coupon",
        description="Apply a coupon code to the cart",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'coupon_code': {'type': 'string', 'example': 'SAVE20'},
                },
                'required': ['coupon_code']
            }
        },
        responses={200: OpenApiTypes.OBJECT},
        tags=['Cart'],
    )
    @action(detail=False, methods=['post'])
    def apply_coupon(self, request):
        """Apply coupon code to cart"""
        coupon_code = request.data.get('coupon_code', '').strip().upper()

        if not coupon_code:
            return Response(
                {'error': 'Coupon code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Import here to avoid circular imports
        from promotions.models import Promotion

        try:
            promotion = Promotion.objects.get(
                code=coupon_code,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
        except Promotion.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired coupon code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check usage limits
        if promotion.max_uses and promotion.times_used >= promotion.max_uses:
            return Response(
                {'error': 'This coupon has reached its usage limit'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = self._get_or_create_cart()

        # Calculate discount
        cart_serializer = CartSerializer(cart)
        subtotal = cart_serializer.data.get('subtotal', 0)

        if promotion.min_purchase_amount and subtotal < promotion.min_purchase_amount:
            return Response(
                {
                    'error': f'Minimum purchase of ${promotion.min_purchase_amount} required',
                    'min_amount': promotion.min_purchase_amount
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate discount amount
        if promotion.discount_type == 'percentage':
            discount_amount = subtotal * (promotion.discount_value / 100)
        else:  # fixed amount
            discount_amount = promotion.discount_value

        return Response({
            'message': 'Coupon applied successfully',
            'coupon_code': coupon_code,
            'discount_type': promotion.discount_type,
            'discount_value': promotion.discount_value,
            'discount_amount': round(discount_amount, 2),
            'subtotal': round(subtotal, 2),
            'new_total': round(subtotal - discount_amount, 2)
        })

    def _check_inventory(self, product_id, variant_id, quantity):
        """Check if sufficient inventory is available"""
        from inventory.models import InventoryItem

        inventory = InventoryItem.objects.filter(
            product_id=product_id,
            variant_id=variant_id
        ).first()

        if not inventory:
            # No inventory tracking, allow the purchase
            return True

        return inventory.quantity_available >= quantity


# ============================================================================
# WISHLIST VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List user wishlists",
        description="Retrieve all wishlists for the authenticated user",
        tags=['Wishlist'],
    ),
    retrieve=extend_schema(
        summary="Get wishlist details",
        description="Retrieve detailed wishlist information including all items",
        tags=['Wishlist'],
    ),
    create=extend_schema(
        summary="Create new wishlist",
        description="Create a new wishlist for the authenticated user",
        tags=['Wishlist'],
    ),
    update=extend_schema(
        summary="Update wishlist",
        description="Update wishlist name or settings",
        tags=['Wishlist'],
    ),
    destroy=extend_schema(
        summary="Delete wishlist",
        description="Delete a wishlist and all its items",
        tags=['Wishlist'],
    ),
)
class WishlistViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing wishlists.

    Users can create multiple wishlists (e.g., "Birthday Wishlist", "Holiday Wishlist").
    One wishlist can be marked as default.
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get wishlists for current user"""
        # Return empty queryset for schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Wishlist.objects.none()

        return Wishlist.objects.filter(customer=self.request.user).prefetch_related('items')

    def get_serializer_class(self):
        if self.action == 'create':
            return WishlistCreateSerializer
        return WishlistSerializer

    def perform_create(self, serializer):
        """Create wishlist for current user"""
        # If this is the first wishlist, make it default
        is_first = not Wishlist.objects.filter(customer=self.request.user).exists()

        wishlist = serializer.save(
            customer=self.request.user,
            is_default=is_first
        )

        return wishlist

    @extend_schema(
        summary="Get default wishlist",
        description="Get the user's default wishlist",
        responses={200: WishlistSerializer},
        tags=['Wishlist'],
    )
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get default wishlist"""
        wishlist = Wishlist.objects.filter(
            customer=request.user,
            is_default=True
        ).first()

        if not wishlist:
            # Create default wishlist if doesn't exist
            wishlist = Wishlist.objects.create(
                customer=request.user,
                name='My Wishlist',
                is_default=True
            )

        serializer = self.get_serializer(wishlist)
        return Response(serializer.data)

    @extend_schema(
        summary="Set as default wishlist",
        description="Set this wishlist as the default",
        responses={200: OpenApiTypes.OBJECT},
        tags=['Wishlist'],
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set wishlist as default"""
        wishlist = self.get_object()

        # Unset other defaults
        Wishlist.objects.filter(customer=request.user).update(is_default=False)

        # Set this as default
        wishlist.is_default = True
        wishlist.save()

        return Response({
            'message': 'Wishlist set as default',
            'wishlist_id': wishlist.id,
            'name': wishlist.name
        })

    @extend_schema(
        summary="Add item to wishlist",
        description="Add a product to the wishlist",
        request=AddToWishlistSerializer,
        responses={200: WishlistSerializer},
        tags=['Wishlist'],
    )
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add item to wishlist"""
        wishlist = self.get_object()

        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        variant_id = serializer.validated_data.get('variant_id')
        note = serializer.validated_data.get('note', '')
        priority = serializer.validated_data.get('priority', 0)

        # Check if item already exists
        existing_item = WishlistItem.objects.filter(
            wishlist=wishlist,
            product_id=product_id,
            variant_id=variant_id
        ).first()

        if existing_item:
            return Response(
                {'error': 'Item already in wishlist'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add item
        WishlistItem.objects.create(
            wishlist=wishlist,
            product_id=product_id,
            variant_id=variant_id,
            note=note,
            priority=priority
        )

        # Return updated wishlist
        wishlist_serializer = WishlistSerializer(wishlist, context={'request': request})
        return Response(wishlist_serializer.data)

    @extend_schema(
        summary="Remove item from wishlist",
        description="Remove a specific item from the wishlist",
        responses={200: WishlistSerializer},
        tags=['Wishlist'],
    )
    @action(detail=True, methods=['delete'], url_path='remove-item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        """Remove item from wishlist"""
        wishlist = self.get_object()

        try:
            item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
            item.delete()
        except WishlistItem.DoesNotExist:
            return Response(
                {'error': 'Wishlist item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Return updated wishlist
        wishlist_serializer = WishlistSerializer(wishlist, context={'request': request})
        return Response(wishlist_serializer.data)

    @extend_schema(
        summary="Move item to cart",
        description="Move a wishlist item to the shopping cart",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'quantity': {'type': 'integer', 'example': 1, 'default': 1},
                },
            }
        },
        responses={200: OpenApiTypes.OBJECT},
        tags=['Wishlist'],
    )
    @action(detail=True, methods=['post'], url_path='move-to-cart/(?P<item_id>[^/.]+)')
    def move_to_cart(self, request, pk=None, item_id=None):
        """Move wishlist item to cart"""
        wishlist = self.get_object()

        try:
            wishlist_item = WishlistItem.objects.get(id=item_id, wishlist=wishlist)
        except WishlistItem.DoesNotExist:
            return Response(
                {'error': 'Wishlist item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        quantity = request.data.get('quantity', 1)

        # Get or create cart
        cart, created = Cart.objects.get_or_create(customer=request.user)

        # Get product price
        product = wishlist_item.product
        unit_price = product.sale_price or product.regular_price

        if wishlist_item.variant:
            unit_price = wishlist_item.variant.sale_price or wishlist_item.variant.price

        # Add to cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=wishlist_item.product,
            variant=wishlist_item.variant,
            defaults={
                'quantity': quantity,
                'unit_price': unit_price
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        # Remove from wishlist
        wishlist_item.delete()

        return Response({
            'message': 'Item moved to cart successfully',
            'product_name': product.name,
            'quantity': quantity
        })

    @extend_schema(
        summary="Clear wishlist",
        description="Remove all items from the wishlist",
        responses={200: OpenApiTypes.OBJECT},
        tags=['Wishlist'],
    )
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Clear all items from wishlist"""
        wishlist = self.get_object()
        items_count = wishlist.items.count()
        wishlist.items.all().delete()

        return Response({
            'message': 'Wishlist cleared successfully',
            'items_removed': items_count
        })
