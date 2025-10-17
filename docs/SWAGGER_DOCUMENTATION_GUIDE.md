# 📚 Swagger/OpenAPI Documentation Guide

## Overview

Your Django multi-tenant e-commerce platform now has **beautiful, interactive API documentation** powered by `drf-spectacular` (OpenAPI 3.0 specification).

---

## 🚀 Quick Access

### After running `python manage.py runserver`, access:

| Interface | URL | Description |
|-----------|-----|-------------|
| **Swagger UI** | `http://localhost:8000/api/docs/` | Interactive API testing interface |
| **ReDoc** | `http://localhost:8000/api/redoc/` | Beautiful, clean documentation |
| **OpenAPI Schema** | `http://localhost:8000/api/schema/` | Raw OpenAPI 3.0 JSON schema |

---

## 🎯 Features

### ✅ What's Included:

- **Interactive API Testing** - Try API calls directly from the browser
- **Authentication Support** - Test authenticated endpoints with JWT tokens
- **Request/Response Examples** - See sample data for all endpoints
- **Schema Validation** - Automatic validation of request/response formats
- **Filtering & Search** - Find endpoints quickly
- **Model Schemas** - View all data models and their fields
- **Error Examples** - See possible error responses
- **Rate Limit Info** - View rate limiting details
- **Multi-Server Support** - Switch between dev/production servers

---

## 🔐 Using Authentication in Swagger

### Step 1: Register or Login
```bash
# Use Swagger UI to register
POST /api/auth/register/
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "SecureP@ssw0rd123!",
  "password2": "SecureP@ssw0rd123!",
  "first_name": "Test",
  "last_name": "User"
}

# Or login
POST /api/auth/login/
{
  "username": "testuser",
  "password": "SecureP@ssw0rd123!"
}
```

### Step 2: Authorize in Swagger UI
1. Click the **"Authorize"** button (🔓 lock icon) at the top right
2. Enter your access token in the format: `Bearer <your_access_token>`
3. Click **"Authorize"**
4. Click **"Close"**

### Step 3: Test Authenticated Endpoints
Now all API calls will include your authentication token automatically!

---

## 📖 How to Use Swagger UI

### 1. **Browse Endpoints**
- Endpoints are organized by tags (Authentication, Products, Orders, etc.)
- Click on any section to expand and see available endpoints

### 2. **Test an Endpoint**
- Click on any endpoint to expand it
- Click **"Try it out"**
- Fill in required parameters
- Click **"Execute"**
- View the response below

### 3. **View Models**
- Scroll to the bottom to see **"Schemas"**
- Click on any model to see its structure
- View required fields, data types, and constraints

### 4. **Download OpenAPI Spec**
- Click **"Download"** at the top to get the OpenAPI JSON/YAML file
- Use it with Postman, Insomnia, or other API clients

---

## 🎨 Customizing Documentation

### Adding Documentation to Your Views

#### Method 1: Using Docstrings
```python
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema

class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing products.

    list: Get all products
    retrieve: Get a specific product by ID
    create: Create a new product
    update: Update an existing product
    partial_update: Partially update a product
    destroy: Delete a product
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

#### Method 2: Using @extend_schema Decorator
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

class ProductViewSet(viewsets.ModelViewSet):

    @extend_schema(
        summary="List all products",
        description="Retrieve a paginated list of all active products",
        parameters=[
            OpenApiParameter(
                name='category',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID'
            ),
            OpenApiParameter(
                name='is_featured',
                type=bool,
                location=OpenApiParameter.QUERY,
                description='Filter featured products'
            ),
        ],
        tags=['Products'],
    )
    def list(self, request):
        """List all products with filtering options"""
        pass

    @extend_schema(
        summary="Create a new product",
        description="Create a new product. Requires staff permissions.",
        request=ProductCreateSerializer,
        responses={
            201: ProductDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        tags=['Products'],
    )
    def create(self, request):
        """Create a new product"""
        pass
```

#### Method 3: Adding Examples
```python
from drf_spectacular.utils import extend_schema, OpenApiExample

@extend_schema(
    summary="User login",
    description="Authenticate user and receive JWT tokens",
    request=LoginSerializer,
    responses={
        200: CustomTokenObtainPairSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Valid Login',
            value={
                'username': 'johndoe',
                'password': 'SecureP@ssw0rd123!'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Successful Response',
            value={
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                'user': {
                    'id': 1,
                    'username': 'johndoe',
                    'email': 'john@example.com'
                }
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
    tags=['Authentication'],
)
def post(self, request):
    """Login endpoint"""
    pass
```

---

## 🏷️ Organizing with Tags

### Define Tags in settings.py (Already Done!)
```python
SPECTACULAR_SETTINGS = {
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and security'},
        {'name': 'Products', 'description': 'Product catalog management'},
        {'name': 'Orders', 'description': 'Order management'},
        # ... more tags
    ],
}
```

### Apply Tags to Views
```python
from drf_spectacular.utils import extend_schema_view, extend_schema

@extend_schema_view(
    list=extend_schema(tags=['Products']),
    retrieve=extend_schema(tags=['Products']),
    create=extend_schema(tags=['Products']),
)
class ProductViewSet(viewsets.ModelViewSet):
    pass
```

---

## 📋 Adding Custom Parameters

### Query Parameters
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search products by name or description',
            required=False,
        ),
        OpenApiParameter(
            name='min_price',
            type=OpenApiTypes.DECIMAL,
            location=OpenApiParameter.QUERY,
            description='Filter products with price greater than or equal to this value',
            required=False,
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Order by field. Prefix with - for descending. Example: -created_at',
            enum=['name', '-name', 'price', '-price', 'created_at', '-created_at'],
            required=False,
        ),
    ],
)
def list(self, request):
    pass
```

### Path Parameters
```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='product_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='Unique product identifier',
            required=True,
        ),
    ],
)
def retrieve(self, request, pk=None):
    pass
```

### Header Parameters
```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='X-API-Version',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            description='API version',
            required=False,
        ),
    ],
)
def custom_action(self, request):
    pass
```

---

## 🔧 Advanced Configuration

### Exclude Endpoints from Documentation
```python
from drf_spectacular.utils import extend_schema

class InternalViewSet(viewsets.ModelViewSet):

    @extend_schema(exclude=True)
    def internal_method(self, request):
        """This won't appear in documentation"""
        pass
```

### Custom Response Schemas
```python
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

@extend_schema(
    responses={
        200: inline_serializer(
            name='CustomResponse',
            fields={
                'status': serializers.CharField(),
                'message': serializers.CharField(),
                'data': serializers.DictField(),
            }
        )
    }
)
def custom_view(request):
    pass
```

### Versioning Support
```python
# In settings.py
SPECTACULAR_SETTINGS = {
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]',
    'VERSION': '1.0.0',
}

# In urls.py
urlpatterns = [
    path('api/v1/', include('api.v1.urls')),
    path('api/v2/', include('api.v2.urls')),
]
```

---

## 🎨 Swagger UI Customization

### Change Theme Colors
Edit in `settings.py`:
```python
SPECTACULAR_SETTINGS = {
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'syntaxHighlight.theme': 'agate',  # Options: agate, arta, monokai, nord, obsidian
    },
}
```

### Custom Logo/Branding
```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'Your Company API',
    'DESCRIPTION': 'Your custom description',
    'EXTERNAL_DOCS': {
        'description': 'Full Documentation',
        'url': 'https://docs.yourcompany.com'
    },
}
```

---

## 📥 Generating Static Documentation

### Generate OpenAPI Schema File
```bash
# Generate schema.yaml
python manage.py spectacular --file schema.yaml

# Generate schema.json
python manage.py spectacular --format openapi-json --file schema.json

# Validate schema
python manage.py spectacular --validate
```

### Use with Other Tools

#### Postman
1. Generate schema: `python manage.py spectacular --file schema.yaml`
2. Open Postman → Import → Upload schema.yaml
3. All endpoints will be imported as a collection

#### Insomnia
1. Generate schema
2. Import into Insomnia
3. Use for testing

#### Code Generators
```bash
# Generate client SDKs
npx openapi-generator-cli generate \
  -i http://localhost:8000/api/schema/ \
  -g typescript-axios \
  -o ./frontend/src/api
```

---

## 🐛 Troubleshooting

### Issue: "No operations found"
**Solution**: Ensure views have proper serializer_class and queryset

### Issue: Authentication not working in Swagger
**Solution**: Check that `bearerAuth` is properly configured in SPECTACULAR_SETTINGS

### Issue: Missing endpoints
**Solution**:
- Check that views are registered in routers
- Ensure URLs are included in main urls.py
- Run `python manage.py spectacular --validate` to check for errors

### Issue: Wrong request/response schemas
**Solution**:
- Use `@extend_schema` to explicitly define schemas
- Check serializer definitions
- Add proper docstrings

---

## 📚 Best Practices

### 1. **Always Add Descriptions**
```python
class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer with full details including images and variants.
    Used for product detail views.
    """
    class Meta:
        model = Product
        fields = '__all__'
```

### 2. **Use Explicit Examples**
```python
@extend_schema(
    examples=[
        OpenApiExample(
            'Example Product',
            value={
                'name': 'Wireless Mouse',
                'price': 29.99,
                'stock': 150
            }
        )
    ]
)
```

### 3. **Document Error Responses**
```python
@extend_schema(
    responses={
        200: ProductSerializer,
        400: OpenApiTypes.OBJECT,  # Bad Request
        401: OpenApiTypes.OBJECT,  # Unauthorized
        403: OpenApiTypes.OBJECT,  # Forbidden
        404: OpenApiTypes.OBJECT,  # Not Found
        500: OpenApiTypes.OBJECT,  # Server Error
    }
)
```

### 4. **Group Related Endpoints**
```python
@extend_schema_view(
    list=extend_schema(tags=['Products'], summary='List products'),
    retrieve=extend_schema(tags=['Products'], summary='Get product'),
    create=extend_schema(tags=['Products'], summary='Create product'),
)
```

### 5. **Keep Documentation Updated**
- Run `python manage.py spectacular --validate` regularly
- Update examples when API changes
- Review documentation before releases

---

## 🔗 Useful Links

- **drf-spectacular Docs**: https://drf-spectacular.readthedocs.io/
- **OpenAPI Specification**: https://swagger.io/specification/
- **Swagger UI**: https://swagger.io/tools/swagger-ui/
- **ReDoc**: https://redocly.com/redoc

---

## 🎉 Your Documentation URLs

| Interface | URL | Use Case |
|-----------|-----|----------|
| **Swagger UI** | http://localhost:8000/api/docs/ | Interactive testing |
| **ReDoc** | http://localhost:8000/api/redoc/ | Clean reading |
| **Schema JSON** | http://localhost:8000/api/schema/ | Download/Import |

---

**Your API documentation is now live and beautiful!** 🎨📚

Visit `http://localhost:8000/api/docs/` to see your interactive API documentation!

