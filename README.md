# Multi-Tenant E-Commerce Platform

A comprehensive, production-ready multi-tenant e-commerce platform built with Django and Django REST Framework. This platform enables multiple independent online stores to operate on a single codebase with complete data isolation, advanced features, and AI-powered recommendations.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Django Version](https://img.shields.io/badge/django-5.0%2B-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌟 Key Features

### Multi-Tenancy Architecture
- **Schema-based isolation** - Complete data separation per tenant
- **Subdomain routing** - Automatic tenant detection
- **Shared/tenant-specific apps** - Flexible app configuration
- **Custom domain support** - Brand your stores

### Product Management
- **Multiple product types** - Simple, variable, grouped, digital
- **Variant support** - Colors, sizes, attributes
- **Categories & brands** - Hierarchical organization
- **Product reviews** - Customer ratings and reviews
- **Advanced filtering** - Search, sort, filter by multiple criteria
- **SEO optimization** - Meta tags, structured data

### Inventory Management
- **Multi-warehouse support** - Multiple storage locations
- **Real-time tracking** - Accurate stock levels
- **Stock movements** - Complete audit trail
- **Low stock alerts** - Automatic notifications
- **Purchase orders** - Supplier management
- **Inventory reservations** - Hold stock for pending orders

### Order Management
- **Complete order lifecycle** - Pending → Processing → Shipped → Delivered
- **Order tracking** - Real-time status updates
- **Invoice generation** - Automatic invoicing
- **Shipping zones** - Country-based shipping
- **Shipping calculation** - Dynamic cost calculation
- **Order cancellation** - With inventory release

### Payment Processing
- **Multi-gateway support** - Stripe, Paystack, PayPal
- **Secure transactions** - PCI compliance
- **Payment tracking** - Complete transaction history
- **Refund processing** - Full and partial refunds
- **Webhook handling** - Automatic status updates
- **Payment retry** - Failed payment recovery

### Promotions & Discounts
- **Multiple discount types** - Percentage, fixed, BOGO, free shipping
- **Coupon management** - Single-use and bulk generation
- **Customer targeting** - Group-specific promotions
- **Usage limits** - Total and per-customer limits
- **Promotion analytics** - Performance tracking

### AI-Powered Recommendations
- **Collaborative filtering** - Users who bought X also bought Y
- **Content-based filtering** - Similar product recommendations
- **Trending products** - Popular items algorithm
- **Personalized recommendations** - Hybrid ML approach
- **Frequently bought together** - Market basket analysis
- **Behavior tracking** - Comprehensive analytics

### Customer Management
- **Customer accounts** - Registration and profiles
- **Address management** - Multiple addresses
- **Customer groups** - Segmentation and targeting
- **Order history** - Complete purchase records
- **Wishlist** - Save for later
- **Loyalty points** - Reward system

### Shopping Cart
- **Session-based carts** - Anonymous shopping
- **User-based carts** - Persistent carts
- **Cart merging** - Combine anonymous and user carts
- **Inventory validation** - Real-time stock checks
- **Cart abandonment tracking** - Recovery campaigns

### Security & Authentication
- **JWT authentication** - Secure token-based auth
- **Two-factor authentication** - Enhanced security
- **Email verification** - Account confirmation
- **Password reset** - Secure recovery flow
- **Account lockout** - Brute force protection
- **Rate limiting** - DDoS prevention
- **Audit logging** - Complete security trail

### API & Documentation
- **RESTful API** - Clean, consistent endpoints
- **Swagger/OpenAPI** - Interactive documentation
- **API versioning** - Backward compatibility
- **Comprehensive filtering** - Django filters
- **Pagination** - Efficient data handling
- **CORS support** - Cross-origin requests

---

## 🛠️ Tech Stack

### Backend
- **Django 5.0+** - Python web framework
- **Django REST Framework** - API development
- **django-tenants** - Multi-tenancy support
- **PostgreSQL** - Primary database
- **Redis** - Caching and sessions
- **Celery** - Background task processing

### Authentication & Security
- **djangorestframework-simplejwt** - JWT authentication
- **django-cors-headers** - CORS support
- **python-decouple** - Environment management

### API Documentation
- **drf-spectacular** - OpenAPI/Swagger documentation

### Filtering & Search
- **django-filter** - Advanced filtering

### Payment Gateways
- **stripe** - Stripe integration
- **paystack** - Paystack integration
- **paypal** - PayPal integration (SDK)

---

## 📁 Project Structure

```
django-multi-tenants/
├── api/                        # Core API configuration
│   ├── authentication.py       # Custom auth backends
│   ├── permissions.py          # Custom permissions (15+ classes)
│   ├── throttles.py           # Rate limiting
│   ├── urls.py                # Main API routing
│   └── views.py               # Authentication views
├── tenants/                    # Multi-tenancy app
│   └── models.py              # Tenant and Domain models
├── products/                   # Product management
│   ├── models.py              # Product, Category, Brand, Review
│   ├── serializers.py         # Product serializers
│   ├── views.py               # Product CRUD + Reviews
│   ├── filters.py             # Product filtering
│   └── urls.py                # Product endpoints
├── inventory/                  # Inventory management
│   ├── models.py              # Warehouse, Stock, PO
│   ├── serializers.py         # Inventory serializers
│   ├── views.py               # Inventory CRUD
│   ├── filters.py             # Inventory filtering
│   └── urls.py                # Inventory endpoints
├── orders/                     # Order management
│   ├── models.py              # Order, OrderItem, Shipping
│   ├── serializers.py         # Order serializers
│   ├── views.py               # Order CRUD + tracking
│   ├── filters.py             # Order filtering
│   └── urls.py                # Order endpoints
├── payments/                   # Payment processing
│   ├── models.py              # Payment, Refund
│   ├── serializers.py         # Payment serializers
│   ├── views.py               # Payment processing
│   ├── filters.py             # Payment filtering
│   ├── gateways/              # Payment gateway implementations
│   │   ├── stripe_gateway.py
│   │   ├── paystack_gateway.py
│   │   └── paypal_gateway.py
│   └── urls.py                # Payment endpoints
├── promotions/                 # Promotions & coupons
│   ├── models.py              # Promotion, Coupon
│   ├── serializers.py         # Promotion serializers
│   ├── views.py               # Promotion CRUD + validation
│   ├── filters.py             # Promotion filtering
│   └── urls.py                # Promotion endpoints
├── recommendations/            # AI recommendation engine
│   ├── models.py              # Interaction, RecommendationLog
│   ├── serializers.py         # Recommendation serializers
│   ├── views.py               # Recommendation algorithms
│   └── urls.py                # Recommendation endpoints
├── customers/                  # Customer management
│   ├── models.py              # Customer, Address, Group
│   ├── serializers.py         # Customer serializers
│   ├── views.py               # Customer CRUD
│   ├── filters.py             # Customer filtering
│   └── urls.py                # Customer endpoints
├── cart/                       # Shopping cart
│   ├── models.py              # Cart, CartItem, Wishlist
│   ├── serializers.py         # Cart serializers
│   ├── views.py               # Cart management
│   └── urls.py                # Cart endpoints
├── config/                     # Django settings
│   ├── settings.py            # Main settings
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI configuration
├── docs/                       # Documentation
│   └── project-description.md # Project specification
├── requirements.txt            # Python dependencies
├── manage.py                  # Django management script
└── README.md                  # This file
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/django-multi-tenants.git
cd django-multi-tenants
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root (optional - all settings have defaults):

> **Note**: The application uses `os.getenv()` for environment variables. You can either:
> - Create a `.env` file and load it using `python-dotenv`
> - Set environment variables directly in your system
> - Use the default values (suitable for development)

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_NAME=ecommerce_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

# Payment Gateways
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
PAYSTACK_WEBHOOK_SECRET=...

PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=sandbox

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Database Setup
```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE ecommerce_db;
\q

# Run migrations for shared apps
python manage.py migrate_schemas --shared

# Run migrations for tenant apps
python manage.py migrate_schemas
```

**Note**: You'll need to create tenants using Django shell or create a custom management command. See the [Multi-Tenancy Setup](#-multi-tenancy-setup) section below for details.

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker (optional)
celery -A config worker -l info

# Terminal 3: Celery beat (optional)
celery -A config beat -l info

# Terminal 4: Flower - Celery monitoring (optional)
celery -A config flower
```

Access the application:
- **Main Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Flower Monitoring**: http://localhost:5555 (if running)

---

## 📋 Implementation Status

### ✅ Fully Implemented
- Multi-tenant architecture with schema-based isolation
- Complete product management (CRUD, categories, brands, reviews)
- Inventory management (warehouses, stock movements, alerts, purchase orders)
- Order management (full lifecycle, tracking, invoicing)
- Payment processing (Stripe, Paystack, PayPal integration)
- Promotions & coupon system (multiple discount types)
- AI-powered recommendations (5 algorithms)
- Customer management (accounts, addresses, groups)
- Shopping cart & wishlist
- Comprehensive authentication & security (JWT, 2FA, rate limiting)
- API documentation (Swagger/OpenAPI)
- Celery background task infrastructure
- Redis caching for recommendations

### 🚧 In Development
- Email notification tasks (abandoned cart, order updates)
- Email template system
- Tenant creation management command
- Docker containerization
- Advanced analytics dashboard

### 📝 Planned Features
- GraphQL API support
- Multi-language support (i18n)
- Advanced reporting & exports
- Marketplace features
- Mobile app integration
- Real-time notifications (WebSockets)

---

## 📚 API Documentation

### Interactive Documentation
Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### API Endpoints Overview

#### Authentication (`/api/v1/auth/`)
- `POST /register/` - User registration
- `POST /login/` - User login (JWT)
- `POST /logout/` - User logout
- `POST /refresh/` - Refresh JWT token
- `POST /verify-email/` - Email verification
- `POST /forgot-password/` - Password reset request
- `POST /reset-password/` - Password reset
- `POST /2fa/enable/` - Enable 2FA
- `POST /2fa/verify/` - Verify 2FA code

#### Products (`/api/v1/products/`)
- `GET /products/` - List products
- `POST /products/` - Create product (admin)
- `GET /products/{id}/` - Get product details
- `PUT /products/{id}/` - Update product (admin)
- `DELETE /products/{id}/` - Delete product (admin)
- `GET /categories/` - List categories
- `GET /brands/` - List brands
- `GET /reviews/` - List reviews
- `POST /products/{id}/reviews/` - Add review

#### Inventory (`/api/v1/inventory/`)
- `GET /warehouses/` - List warehouses
- `GET /inventory-items/` - List inventory
- `POST /stock-movements/` - Record stock movement
- `GET /stock-alerts/` - Get low stock alerts
- `GET /purchase-orders/` - List purchase orders
- `POST /purchase-orders/` - Create PO (admin)

#### Orders (`/api/v1/orders/`)
- `GET /orders/` - List orders
- `POST /orders/` - Create order
- `GET /orders/{id}/` - Get order details
- `POST /orders/{id}/cancel/` - Cancel order
- `GET /orders/{id}/track/` - Track order
- `GET /orders/{id}/invoice/` - Get invoice
- `POST /orders/{id}/reorder/` - Reorder
- `GET /shipping-zones/` - List shipping zones
- `POST /shipping-zones/calculate/` - Calculate shipping

#### Payments (`/api/v1/payments/`)
- `GET /payments/` - List payments
- `POST /payments/create_intent/` - Create payment intent
- `POST /payments/confirm/` - Confirm payment
- `POST /payments/{id}/verify/` - Verify payment
- `GET /refunds/` - List refunds
- `POST /refunds/` - Create refund (admin)
- `POST /webhooks/{gateway}/` - Payment webhooks

#### Promotions (`/api/v1/promotions/`)
- `GET /promotions/` - List promotions
- `GET /promotions/active/` - Get active promotions
- `GET /promotions/featured/` - Get featured promotions
- `POST /coupons/validate/` - Validate coupon
- `POST /coupons/apply/` - Apply coupon to order
- `POST /coupons/bulk_generate/` - Bulk generate coupons (admin)

#### Recommendations (`/api/v1/recommendations/`)
- `POST /track/` - Track interaction
- `POST /get-recommendations/` - Get recommendations
- `POST /similar-products/` - Get similar products
- `POST /trending/` - Get trending products
- `POST /personalized/` - Get personalized recommendations
- `POST /frequently-bought-together/` - Get bundle suggestions
- `POST /recently-viewed/` - Get recently viewed

#### Customers (`/api/v1/customers/`)
- `GET /customers/` - List customers (admin)
- `GET /customers/me/` - Get current user profile
- `PUT /customers/me/` - Update profile
- `GET /addresses/` - List addresses
- `POST /addresses/` - Add address
- `GET /groups/` - List customer groups

#### Cart (`/api/v1/cart/` & `/api/v1/wishlist/`)
- `GET /cart/` - Get cart
- `POST /cart/add/` - Add to cart
- `PUT /cart/update/` - Update cart item
- `DELETE /cart/remove/{id}/` - Remove from cart
- `POST /cart/clear/` - Clear cart
- `GET /wishlist/` - Get wishlist
- `POST /wishlist/add/` - Add to wishlist

---

## 🏢 Multi-Tenancy Setup

### Creating a New Tenant

#### Using Django Shell
```python
from tenants.models import Tenant, Domain

# Create tenant
tenant = Tenant.objects.create(
    schema_name='tenant1',
    name='Tenant 1',
    business_name='Tenant 1 Store',
    business_email='admin@tenant1.com',
    business_phone='+1234567890',
    currency='USD',
    timezone='UTC'
)

# Create domain
domain = Domain.objects.create(
    domain='tenant1.localhost',
    tenant=tenant,
    is_primary=True
)
```

### Testing Multi-Tenancy

Add to your `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):
```
127.0.0.1 tenant1.localhost
127.0.0.1 tenant2.localhost
```

Access tenants:
- Tenant 1: http://tenant1.localhost:8000
- Tenant 2: http://tenant2.localhost:8000

---

## 💻 Usage Examples

### Creating an Order Flow

```python
# 1. Add items to cart
POST /api/v1/cart/add/
{
  "product_id": 1,
  "quantity": 2,
  "variant_id": 3
}

# 2. Validate coupon (optional)
POST /api/v1/promotions/coupons/validate/
{
  "code": "SAVE20",
  "cart_total": 100.00
}

# 3. Calculate shipping
POST /api/v1/orders/shipping-zones/calculate/
{
  "country": "US",
  "subtotal": 100.00
}

# 4. Create order
POST /api/v1/orders/orders/
{
  "shipping_amount": 10.00,
  "tax_amount": 8.00,
  "payment_method": "card",
  "billing_address": {...},
  "shipping_address": {...},
  "coupon_code": "SAVE20"
}

# 5. Create payment intent
POST /api/v1/payments/payments/create_intent/
{
  "order_id": 123,
  "payment_method": "card",
  "gateway": "stripe"
}

# 6. Confirm payment (after user completes payment)
POST /api/v1/payments/payments/confirm/
{
  "payment_intent_id": "pi_abc123",
  "gateway": "stripe"
}

# 7. Track order
GET /api/v1/orders/orders/123/track/
```

### Getting Recommendations

```python
# Track user interaction
POST /api/v1/recommendations/track/
{
  "product_id": 123,
  "interaction_type": "view",
  "source": "homepage"
}

# Get personalized recommendations
POST /api/v1/recommendations/personalized/
{
  "limit": 10,
  "page_type": "homepage"
}

# Get similar products
POST /api/v1/recommendations/similar-products/
{
  "product_id": 123,
  "limit": 5
}

# Get trending products
POST /api/v1/recommendations/trending/
{
  "days": 7,
  "limit": 20
}
```

---

## 🔒 Security Features

### Implemented Security Measures

1. **Authentication Security**
   - JWT token authentication
   - Token refresh mechanism
   - Two-factor authentication (2FA)
   - Email verification
   - Account lockout after failed attempts
   - Password strength validation

2. **API Security**
   - Rate limiting (15+ throttle classes)
   - CORS configuration
   - CSRF protection
   - Input validation
   - SQL injection prevention
   - XSS protection

3. **Payment Security**
   - PCI compliance (no raw card storage)
   - Webhook signature verification
   - Transaction audit trail
   - Secure payment gateway integration

4. **Data Security**
   - Tenant data isolation (schema-based)
   - Encrypted sensitive data
   - Secure password hashing
   - Audit logging
   - GDPR compliance ready

5. **Infrastructure Security**
   - HTTPS enforcement (production)
   - HSTS headers
   - Secure cookies
   - Environment variable configuration

---

## ⚡ Performance Optimization

### Caching Strategy
- **Redis caching** for recommendations (30 min - 1 hour TTL)
- **Query optimization** - select_related, prefetch_related
- **Database indexing** - Composite indexes on frequently queried fields
- **API pagination** - Efficient data handling

### Background Tasks (Celery)
The platform uses Celery with Redis for asynchronous task processing:

**Configured Task Queues:**
- `recommendations` - ML-based recommendation updates
- `orders` - Order processing and notifications
- `cart` - Cart cleanup and abandoned cart recovery
- `inventory` - Stock level updates and alerts
- `promotions` - Promotion analytics and expiration
- `customers` - Customer data processing

**Implemented Tasks:**
- Recommendation precomputation (every 1 hour)
- Product similarity calculations
- Trending products analysis
- Personalized recommendations

**Scheduled Tasks (Celery Beat):**
- `update_product_recommendations` - Runs hourly to refresh cached recommendations
- `clear_recommendation_cache` - Manual cache clearing task

---

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test products
python manage.py test orders

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 📊 Monitoring & Analytics

### Available Analytics

1. **Product Analytics**
   - View counts
   - Sales performance
   - Rating statistics
   - Popular products

2. **Order Analytics**
   - Order summary
   - Revenue tracking
   - Order status distribution

3. **Customer Analytics**
   - Behavior analysis
   - Category preferences
   - Brand preferences
   - Conversion rates

4. **Recommendation Analytics**
   - Click-through rates
   - Conversion rates
   - Algorithm performance
   - A/B testing results

5. **Promotion Analytics**
   - Usage statistics
   - Discount given
   - Most used promotions

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL production database
- [ ] Configure Redis for production
- [ ] Set up static file serving (S3/CDN)
- [ ] Configure email service (SendGrid/AWS SES)
- [ ] Set up SSL/HTTPS
- [ ] Configure payment gateway production keys
- [ ] Set up monitoring (Sentry, New Relic)
- [ ] Configure backup strategy
- [ ] Set up logging
- [ ] Configure Celery workers
- [ ] Set up load balancer (if needed)

### Docker Deployment

> **Note**: Docker configuration is currently in development. A complete `docker-compose.yml` with all services will be available soon.

**Planned Docker Setup:**
- PostgreSQL container for database
- Redis container for caching and Celery broker
- Django web application container
- Celery worker containers (multiple queues)
- Celery beat scheduler container
- Flower monitoring container
- Nginx reverse proxy (production)

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Migration Errors
```bash
# If you encounter migration conflicts, reset migrations for tenant schemas
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
```

#### 2. Redis Connection Error
```bash
# Make sure Redis is running
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

#### 3. Celery Not Processing Tasks
```bash
# Check Celery worker is running
celery -A config worker -l info

# Check if Redis broker is accessible
celery -A config inspect active
```

#### 4. Import Errors for Payment Gateways
```bash
# Ensure all payment gateway packages are installed
pip install stripe pypaystack2 paypalrestsdk
```

#### 5. Schema Does Not Exist Error
This usually means you haven't created a tenant yet. Create one using Django shell:
```python
python manage.py shell
>>> from tenants.models import Tenant, Domain
>>> tenant = Tenant.objects.create(schema_name='public', name='Public')
>>> Domain.objects.create(domain='localhost', tenant=tenant, is_primary=True)
```

#### 6. Static Files Not Loading
```bash
python manage.py collectstatic --noinput
```

### Getting Help
- Check the `/docs` directory for detailed documentation
- Review API documentation at `/api/docs/`
- Open an issue on GitHub with detailed error logs
- Include your Python version, Django version, and OS

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards
- Follow PEP 8 style guide
- Write comprehensive docstrings
- Add unit tests for new features
- Update documentation as needed

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

---

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- django-tenants for multi-tenancy support
- All open-source contributors

---

## 📞 Support

For support, email support@yourdomain.com or open an issue on GitHub.

---

## 🗺️ Roadmap

### Current Sprint (In Progress)
- [ ] Email notification system (abandoned cart, order updates)
- [ ] Email template infrastructure
- [ ] Tenant management command
- [ ] Docker containerization
- [ ] Unit tests for all apps

### Next Sprint (Planned)
- [ ] Advanced analytics dashboard
- [ ] GraphQL API support
- [ ] Multi-language support (i18n)
- [ ] Advanced reporting & exports
- [ ] Real-time notifications (WebSockets)

### Future Releases
- [ ] Mobile app (React Native)
- [ ] Marketplace features
- [ ] Dropshipping integration
- [ ] Advanced SEO tools
- [ ] Multi-currency enhancement
- [ ] AI chatbot integration

---

## 📈 Stats

- **Total Apps**: 10+
- **API Endpoints**: 100+
- **Models**: 30+
- **Custom Permissions**: 15+
- **Recommendation Algorithms**: 5
- **Payment Gateways**: 3
- **Lines of Code**: 15,000+

---

## 🎯 Use Cases

This platform is perfect for:

1. **SaaS E-Commerce** - Multi-tenant marketplace platform
2. **B2B Wholesale** - Supplier and distributor networks
3. **Multi-Brand Retail** - Multiple stores under one roof
4. **Franchise Management** - Centralized franchise system
5. **White-Label Solutions** - Customizable for resellers
6. **Educational Stores** - School/university bookstores
7. **Nonprofit Organizations** - Multiple chapter stores

---

**Built with ❤️ using Django and DRF**

For detailed documentation, visit the `/docs` directory or check out the interactive API documentation at `/api/docs/`.

