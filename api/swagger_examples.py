"""
Example of how to add Swagger documentation to your views

Copy these patterns to your actual views to enhance API documentation
"""

from rest_framework import viewsets, views, generics, status
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)
from drf_spectacular.types import OpenApiTypes


# ============================================================================
# EXAMPLE 1: ViewSet with Complete Documentation
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all products",
        description="Retrieve a paginated list of all active products with filtering and search",
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search by product name, description, or SKU',
                required=False,
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID',
                required=False,
            ),
            OpenApiParameter(
                name='is_featured',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter featured products only',
                required=False,
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Minimum price filter',
                required=False,
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Maximum price filter',
                required=False,
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: name, -name, price, -price, created_at, -created_at',
                required=False,
            ),
        ],
        tags=['Products'],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
    ),
    retrieve=extend_schema(
        summary="Get product details",
        description="Retrieve detailed information about a specific product",
        tags=['Products'],
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    ),
    create=extend_schema(
        summary="Create a new product",
        description="Create a new product. Requires staff permissions.",
        tags=['Products'],
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        }
    ),
    update=extend_schema(
        summary="Update a product",
        description="Update all fields of a product. Requires staff permissions.",
        tags=['Products'],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    ),
    partial_update=extend_schema(
        summary="Partially update a product",
        description="Update specific fields of a product. Requires staff permissions.",
        tags=['Products'],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    ),
    destroy=extend_schema(
        summary="Delete a product",
        description="Permanently delete a product. Requires staff permissions.",
        tags=['Products'],
        responses={
            204: None,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    ),
)
class ProductViewSetExample(viewsets.ModelViewSet):
    """
    API endpoint for managing products.

    Supports CRUD operations with filtering, search, and pagination.
    """
    pass


# ============================================================================
# EXAMPLE 2: Authentication View with Examples
# ============================================================================

class LoginViewExample(views.APIView):
    """User login endpoint"""

    @extend_schema(
        summary="User login",
        description="""
        Authenticate user and receive JWT access and refresh tokens.

        ## Authentication Flow:
        1. Send username/email and password
        2. Receive access token (valid for 15 minutes) and refresh token (valid for 7 days)
        3. Use access token in Authorization header: `Bearer <token>`
        4. Refresh token when access token expires

        ## Two-Factor Authentication:
        If 2FA is enabled for the account, include the `two_factor_code` field.
        """,
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string', 'example': 'johndoe'},
                    'email': {'type': 'string', 'format': 'email', 'example': 'john@example.com'},
                    'password': {'type': 'string', 'format': 'password', 'example': 'SecureP@ssw0rd123!'},
                    'two_factor_code': {'type': 'string', 'example': '123456', 'nullable': True},
                },
                'required': ['password'],
            }
        },
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Login successful',
                examples=[
                    OpenApiExample(
                        'Successful Login',
                        value={
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'user': {
                                'id': 1,
                                'username': 'johndoe',
                                'email': 'john@example.com',
                                'full_name': 'John Doe',
                                'is_verified': True,
                                'is_vip': False
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid input',
                examples=[
                    OpenApiExample(
                        'Invalid Credentials',
                        value={'error': 'Invalid credentials'}
                    ),
                    OpenApiExample(
                        '2FA Required',
                        value={
                            'two_factor_required': True,
                            'message': 'Two-factor authentication code required'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='Authentication failed',
                examples=[
                    OpenApiExample(
                        'Account Locked',
                        value={'error': 'Account temporarily locked due to failed login attempts'}
                    )
                ]
            ),
            429: OpenApiResponse(
                description='Rate limit exceeded',
                examples=[
                    OpenApiExample(
                        'Too Many Requests',
                        value={'error': 'Too many login attempts. Please try again later.'}
                    )
                ]
            ),
        },
        tags=['Authentication'],
    )
    def post(self, request):
        pass


# ============================================================================
# EXAMPLE 3: Custom Action with Multiple Response Types
# ============================================================================

class CartViewSetExample(viewsets.ModelViewSet):
    """Shopping cart operations"""

    @extend_schema(
        summary="Add item to cart",
        description="Add a product (and optionally a variant) to the shopping cart",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'product_id': {'type': 'integer', 'example': 123},
                    'variant_id': {'type': 'integer', 'example': 456, 'nullable': True},
                    'quantity': {'type': 'integer', 'minimum': 1, 'maximum': 999, 'example': 2},
                    'personalization': {
                        'type': 'object',
                        'example': {'engraving': 'Happy Birthday!'},
                        'nullable': True
                    }
                },
                'required': ['product_id', 'quantity']
            }
        },
        responses={
            200: OpenApiResponse(
                description='Item added to cart',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Item added to cart',
                            'cart': {
                                'id': 1,
                                'items_count': 3,
                                'subtotal': '129.99'
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Invalid request',
                examples=[
                    OpenApiExample(
                        'Invalid Quantity',
                        value={'error': 'Quantity must be between 1 and 999'}
                    ),
                    OpenApiExample(
                        'Out of Stock',
                        value={'error': 'Product is currently out of stock'}
                    )
                ]
            ),
            404: OpenApiResponse(
                description='Product not found',
                examples=[
                    OpenApiExample(
                        'Product Not Found',
                        value={'error': 'Product not found or inactive'}
                    )
                ]
            )
        },
        tags=['Cart'],
    )
    def add_to_cart(self, request):
        """Add item to cart custom action"""
        pass


# ============================================================================
# EXAMPLE 4: List View with Filters
# ============================================================================

class OrderListViewExample(generics.ListAPIView):
    """List orders with filtering"""

    @extend_schema(
        summary="List customer orders",
        description="Retrieve a list of orders for the authenticated customer with filtering options",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by order status',
                enum=['pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'],
                required=False,
            ),
            OpenApiParameter(
                name='payment_status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment status',
                enum=['pending', 'paid', 'failed', 'refunded'],
                required=False,
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter orders from this date (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter orders until this date (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='min_total',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Filter orders with total >= this amount',
                required=False,
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination',
                required=False,
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of results per page (max 100)',
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='List of orders',
                examples=[
                    OpenApiExample(
                        'Order List',
                        value={
                            'count': 25,
                            'next': 'http://localhost:8000/api/orders/?page=2',
                            'previous': None,
                            'results': [
                                {
                                    'id': 1,
                                    'order_number': 'ORD-2025-001',
                                    'status': 'delivered',
                                    'total_amount': '299.99',
                                    'created_at': '2025-01-15T10:30:00Z'
                                }
                            ]
                        }
                    )
                ]
            )
        },
        tags=['Orders'],
    )
    def get(self, request):
        pass


# ============================================================================
# EXAMPLE 5: Detail View with Path Parameter
# ============================================================================

class OrderDetailViewExample(generics.RetrieveAPIView):
    """Get order details"""

    @extend_schema(
        summary="Get order details",
        description="Retrieve detailed information about a specific order including items, shipping, and payment info",
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Order ID',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='Order details',
                examples=[
                    OpenApiExample(
                        'Order Detail',
                        value={
                            'id': 1,
                            'order_number': 'ORD-2025-001',
                            'customer': {
                                'id': 1,
                                'name': 'John Doe',
                                'email': 'john@example.com'
                            },
                            'status': 'delivered',
                            'payment_status': 'paid',
                            'subtotal': '279.99',
                            'tax_amount': '20.00',
                            'shipping_amount': '10.00',
                            'total_amount': '309.99',
                            'items': [
                                {
                                    'product_name': 'Wireless Mouse',
                                    'quantity': 2,
                                    'unit_price': '29.99',
                                    'total_price': '59.98'
                                }
                            ],
                            'shipping_address': {
                                'address_line1': '123 Main St',
                                'city': 'New York',
                                'country': 'USA'
                            },
                            'created_at': '2025-01-15T10:30:00Z'
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='Order not found',
                examples=[
                    OpenApiExample(
                        'Not Found',
                        value={'error': 'Order not found'}
                    )
                ]
            ),
            403: OpenApiResponse(
                description='Access denied',
                examples=[
                    OpenApiExample(
                        'Forbidden',
                        value={'error': 'You do not have permission to view this order'}
                    )
                ]
            )
        },
        tags=['Orders'],
    )
    def get(self, request, pk):
        pass


# ============================================================================
# HOW TO APPLY THESE PATTERNS TO YOUR ACTUAL VIEWS
# ============================================================================

"""
1. Import the decorators at the top of your view file:
   from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

2. Add @extend_schema or @extend_schema_view decorator to your views

3. Customize the summary, description, parameters, and responses

4. Add examples for better documentation

5. Group related endpoints with tags

6. Run: python manage.py spectacular --validate
   to check for any issues

7. View your documentation at: http://localhost:8000/api/docs/
"""

