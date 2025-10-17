# Multi-Tenant E-Commerce Platform - Complete Implementation Guide

## Table of Contents
1. System Architecture Overview
2. Multi-Tenancy Implementation
3. Core Models & Database Schema
4. Payment Gateway Integration
5. Comprehensive Inventory System
6. AI Recommendation Engine
7. Key Features & Modules
8. Security & Performance
9. Deployment Strategy

---

## 1. System Architecture Overview

### Tech Stack
- **Backend**: Django 5.0+, Django REST Framework
- **Database**: PostgreSQL (with multi-tenancy support)
- **Cache**: Redis (sessions, caching, celery broker)
- **Task Queue**: Celery + Redis
- **Search**: Elasticsearch or PostgreSQL Full-Text Search
- **Storage**: AWS S3/DigitalOcean Spaces for media
- **AI/ML**: Scikit-learn, TensorFlow/PyTorch for recommendations
- **Payment**: Stripe, Paystack, PayPal, Flutterwave

### Architecture Pattern
```
├── Multi-Tenant Layer (Middleware/Schema Separation)
├── API Layer (DRF with versioning)
├── Business Logic Layer (Services)
├── Data Access Layer (Models/Repositories)
└── External Services (Payment, Email, SMS, AI)
```

---

## 2. Multi-Tenancy Implementation

### Strategy: Schema-Based Multi-Tenancy
Best for data isolation, security, and scalability.

```python
# tenants/models.py
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    created_on = models.DateField(auto_now_add=True)

    # Business details
    business_name = models.CharField(max_length=255)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=20)

    # Subscription & Billing
    subscription_plan = models.CharField(max_length=50, default='basic')
    is_active = models.BooleanField(default=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    # Settings
    currency = models.CharField(max_length=3, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)

    # Features flags
    features = models.JSONField(default=dict)

    auto_create_schema = True
    auto_drop_schema = False

class Domain(DomainMixin):
    pass
```

### Installation & Configuration

```python
# settings.py
INSTALLED_APPS = [
    'django_tenants',
    'tenants',

    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',

    # Shared apps
    'rest_framework',
    'corsheaders',

    # Tenant-specific apps
    'products',
    'inventory',
    'orders',
    'customers',
    'payments',
    'recommendations',
]

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Shared apps (available to all tenants)
SHARED_APPS = [
    'django_tenants',
    'tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
]

# Tenant-specific apps (separate schema per tenant)
TENANT_APPS = [
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'products',
    'inventory',
    'orders',
    'customers',
    'payments',
    'recommendations',
]
```

---

## 3. Core Models & Database Schema

### Product Management

```python
# products/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

class Brand(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    description = models.TextField(blank=True)

class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('simple', 'Simple Product'),
        ('variable', 'Variable Product'),
        ('grouped', 'Grouped Product'),
        ('digital', 'Digital Product'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100, unique=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='simple')

    # Categorization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField('Tag', blank=True)

    # Descriptions
    short_description = models.TextField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    # Pricing
    regular_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    # Digital Product
    is_digital = models.BooleanField(default=False)
    digital_file = models.FileField(upload_to='digital_products/', null=True, blank=True)
    download_limit = models.IntegerField(null=True, blank=True)
    download_expiry_days = models.IntegerField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stats (denormalized for performance)
    view_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)

    # Variant attributes (e.g., Size: Large, Color: Red)
    attributes = models.JSONField()

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Inventory (linked to inventory system)
    is_active = models.BooleanField(default=True)

    image = models.ImageField(upload_to='variants/', null=True, blank=True)

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Inventory System

```python
# inventory/models.py
from django.db import models
from products.models import Product, ProductVariant

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

class InventoryItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)

    # Stock levels
    quantity_on_hand = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)  # Orders not fulfilled
    quantity_available = models.IntegerField(default=0)  # on_hand - reserved

    # Reorder settings
    reorder_level = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)

    # Location in warehouse
    bin_location = models.CharField(max_length=50, blank=True)
    aisle = models.CharField(max_length=20, blank=True)
    shelf = models.CharField(max_length=20, blank=True)

    # Tracking
    last_counted_at = models.DateTimeField(null=True, blank=True)
    last_restocked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['product', 'variant', 'warehouse']]

    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase/Restock'),
        ('sale', 'Sale'),
        ('return', 'Customer Return'),
        ('adjustment', 'Inventory Adjustment'),
        ('damage', 'Damage/Loss'),
        ('transfer', 'Warehouse Transfer'),
        ('manufacturing', 'Manufacturing'),
    ]

    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()

    # References
    reference_type = models.CharField(max_length=50, blank=True)  # 'order', 'purchase_order'
    reference_id = models.IntegerField(null=True, blank=True)

    # Transfer details (if type is transfer)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True,
                                       related_name='outgoing_transfers', blank=True)
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True,
                                     related_name='incoming_transfers', blank=True)

    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StockAlert(models.Model):
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('overstock', 'Overstock'),
    ]

    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)

    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    payment_terms = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```

### Order Management

```python
# orders/models.py
from django.db import models
from customers.models import Customer
from products.models import Product, ProductVariant

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    payment_method = models.CharField(max_length=50)
    payment_gateway = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)

    # Shipping
    shipping_method = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    # Addresses
    billing_address = models.JSONField()
    shipping_address = models.JSONField()

    # Discounts/Coupons
    coupon_code = models.CharField(max_length=50, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    product_name = models.CharField(max_length=255)  # Snapshot
    product_sku = models.CharField(max_length=100)
    variant_name = models.CharField(max_length=255, blank=True)

    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class ShippingZone(models.Model):
    name = models.CharField(max_length=200)
    countries = models.JSONField()  # List of country codes
    is_active = models.BooleanField(default=True)

class ShippingMethod(models.Model):
    zone = models.ForeignKey(ShippingZone, related_name='methods', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    delivery_time = models.CharField(max_length=100, blank=True)

    # Pricing
    is_free = models.BooleanField(default=False)
    flat_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
```

### Customer Management

```python
# customers/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Customer(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Marketing
    accepts_marketing = models.BooleanField(default=False)

    # Stats
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Loyalty
    loyalty_points = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Address(models.Model):
    ADDRESS_TYPES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
    ]

    customer = models.ForeignKey(Customer, related_name='addresses', on_delete=models.CASCADE)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)

    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    is_default = models.BooleanField(default=False)
```

---

## 4. Payment Gateway Integration

### Payment Service Architecture

```python
# payments/services.py
from abc import ABC, abstractmethod
from typing import Dict, Any
import stripe
from paystack import Paystack
from decimal import Decimal

class PaymentGateway(ABC):
    @abstractmethod
    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict) -> Dict:
        pass

    @abstractmethod
    def confirm_payment(self, payment_intent_id: str) -> Dict:
        pass

    @abstractmethod
    def create_refund(self, payment_id: str, amount: Decimal) -> Dict:
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        pass

class StripeGateway(PaymentGateway):
    def __init__(self, api_key: str):
        stripe.api_key = api_key

    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict) -> Dict:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency.lower(),
            metadata=metadata,
            automatic_payment_methods={'enabled': True},
        )
        return {
            'id': intent.id,
            'client_secret': intent.client_secret,
            'status': intent.status,
        }

    def confirm_payment(self, payment_intent_id: str) -> Dict:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            'id': intent.id,
            'status': intent.status,
            'amount': Decimal(intent.amount) / 100,
            'currency': intent.currency,
        }

    def create_refund(self, payment_id: str, amount: Decimal) -> Dict:
        refund = stripe.Refund.create(
            payment_intent=payment_id,
            amount=int(amount * 100),
        )
        return {
            'id': refund.id,
            'status': refund.status,
            'amount': Decimal(refund.amount) / 100,
        }

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str) -> bool:
        try:
            stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return True
        except Exception:
            return False

class PaystackGateway(PaymentGateway):
    def __init__(self, secret_key: str):
        self.paystack = Paystack(secret_key=secret_key)

    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict) -> Dict:
        # Paystack uses kobo (multiply by 100 for NGN)
        response = self.paystack.transaction.initialize(
            email=metadata.get('email'),
            amount=int(amount * 100),
            currency=currency,
            metadata=metadata,
        )
        return {
            'id': response['data']['reference'],
            'authorization_url': response['data']['authorization_url'],
            'access_code': response['data']['access_code'],
        }

    def confirm_payment(self, reference: str) -> Dict:
        response = self.paystack.transaction.verify(reference=reference)
        data = response['data']
        return {
            'id': data['reference'],
            'status': data['status'],
            'amount': Decimal(data['amount']) / 100,
            'currency': data['currency'],
        }

    def create_refund(self, transaction_id: str, amount: Decimal) -> Dict:
        response = self.paystack.refund.create(
            transaction=transaction_id,
            amount=int(amount * 100),
        )
        return {
            'id': response['data']['id'],
            'status': response['data']['status'],
        }

    def verify_webhook(self, payload: bytes, signature: str, secret: str) -> bool:
        import hmac
        import hashlib
        computed_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(computed_signature, signature)

# Factory Pattern
class PaymentGatewayFactory:
    @staticmethod
    def create_gateway(gateway_type: str, credentials: Dict) -> PaymentGateway:
        if gateway_type == 'stripe':
            return StripeGateway(credentials['api_key'])
        elif gateway_type == 'paystack':
            return PaystackGateway(credentials['secret_key'])
        else:
            raise ValueError(f"Unsupported gateway: {gateway_type}")
```

### Payment Models

```python
# payments/models.py
from django.db import models

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey('orders.Order', related_name='payments', on_delete=models.CASCADE)

    gateway = models.CharField(max_length=50)  # stripe, paystack, paypal
    payment_method = models.CharField(max_length=50)  # card, bank_transfer, etc.

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)

    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Gateway response
    transaction_id = models.CharField(max_length=255, unique=True)
    gateway_response = models.JSONField(default=dict)

    # Metadata
    customer_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

class Refund(models.Model):
    payment = models.ForeignKey(Payment, related_name='refunds', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    refund_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 5. AI Recommendation Engine

### Recommendation System Implementation

```python
# recommendations/models.py
from django.db import models

class ProductInteraction(models.Model):
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('cart', 'Add to Cart'),
        ('purchase', 'Purchase'),
        ('wishlist', 'Add to Wishlist'),
        ('search', 'Search'),
    ]

    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)

    # Context
    search_query = models.CharField(max_length=500, blank=True)
    referrer_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['product', 'interaction_type']),
        ]

# recommendations/engine.py
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
from typing import List, Dict
from django.core.cache import cache

class RecommendationEngine:
    def __init__(self):
        self.interaction_weights = {
            'view': 1.0,
            'cart': 3.0,
            'wishlist': 2.0,
            'purchase': 5.0,
        }

    def get_collaborative_recommendations(self, customer_id: int, limit: int = 10) -> List[int]:
        """
        Collaborative Filtering: Users who bought X also bought Y
        """
        cache_key = f'collab_rec_{customer_id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Get customer's purchase history
        customer_products = self._get_customer_products(customer_id)

        # Find similar customers (who bought similar products)
        similar_customers = self._find_similar_customers(customer_id, customer_products)

        # Get products purchased by similar customers
        recommended_products = self._get_products_from_similar_customers(
            similar_customers,
            customer_products,
            limit
        )

        cache.set(cache_key, recommended_products, 3600)  # Cache for 1 hour
        return recommended_products

    def get_content_based_recommendations(self, product_id: int, limit: int = 10) -> List[int]:
        """
        Content-Based Filtering: Products similar to this one
        """
        cache_key = f'content_rec_{product_id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from products.models import Product

        # Get all products with their features
        products = Product.objects.filter(is_active=True).values(
            'id', 'name', 'description', 'category__name', 'brand__name'
        )

        df = pd.DataFrame(products)

        # Create feature text
        df['features'] = (
            df['name'].fillna('') + ' ' +
            df['description'].fillna('') + ' ' +
            df['category__name'].fillna('') + ' ' +
            df['brand__name'].fillna('')
        )

        # TF-IDF Vectorization
        tfidf = TfidfVectorizer(stop_words='english', max_features=100)
        tfidf_matrix = tfidf.fit_transform(df['features'])

        # Calculate similarity
        product_idx = df[df['id'] == product_id].index[0]
        cosine_sim = cosine_similarity(tfidf_matrix[product_idx], tfidf_matrix).flatten()

        # Get top similar products
        similar_indices = cosine_sim.argsort()[-limit-1:-1][::-1]
        recommended_ids = df.iloc[similar_indices]['id'].tolist()

        cache.set(cache_key, recommended_ids, 7200)  # Cache for 2 hours
        return recommended_ids

    def get_trending_products(self, limit: int = 10, days: int = 7) -> List[int]:
        """
        Trending products based on recent interactions
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)

        interactions = ProductInteraction.objects.filter(
            created_at__gte=cutoff_date
        ).values('product_id', 'interaction_type')

        # Calculate weighted scores
        product_scores = defaultdict(float)
        for interaction in interactions:
            product_id = interaction['product_id']
            weight = self.interaction_weights.get(interaction['interaction_type'], 1.0)
            product_scores[product_id] += weight

        # Sort and return top products
        sorted_products = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_products[:limit]]

    def get_personalized_recommendations(self, customer_id: int, limit: int = 10) -> List[int]:
        """
        Hybrid approach: Combine collaborative and content-based filtering
        """
        collab_recs = self.get_collaborative_recommendations(customer_id, limit * 2)

        # If customer has interactions, get content-based recs from their history
        recent_products = self._get_customer_recent_products(customer_id, limit=5)
        content_recs = []
        for product_id in recent_products:
            content_recs.extend(self.get_content_based_recommendations(product_id, limit=5))

        # Combine and deduplicate
        all_recs = list(dict.fromkeys(collab_recs + content_recs))

        # If still not enough, add trending products
        if len(all_recs) < limit:
            trending = self.get_trending_products(limit=limit)
            all_recs.extend([p for p in trending if p not in all_recs])

        return all_recs[:limit]

    def _get_customer_products(self, customer_id: int) -> set:
        from orders.models import OrderItem
        order_items = OrderItem.objects.filter(
            order__customer_id=customer_id,
            order__status='delivered'
        ).values_list('product_id', flat=True)
        return set(order_items)

    def _get_customer_recent_products(self, customer_id: int, limit: int) -> List[int]:
        interactions = ProductInteraction.objects.filter(
            customer_id=customer_id
        ).order_by('-created_at').values_list('product_id', flat=True)[:limit]
        return list(interactions)

    def _find_similar_customers(self, customer_id: int, customer_products: set, limit: int = 50) -> List[int]:
        from orders.models import Order, OrderItem

        # Find customers who bought at least one similar product
        similar_orders = OrderItem.objects.filter(
            product_id__in=customer_products,
            order__status='delivered'
        ).exclude(order__customer_id=customer_id).values_list('order__customer_id', flat=True).distinct()

        # Calculate similarity scores
        customer_similarities = []
        for other_customer_id in set(similar_orders):
            other_products = self._get_customer_products(other_customer_id)
            similarity = len(customer_products & other_products) / len(customer_products | other_products)
            customer_similarities.append((other_customer_id, similarity))

        # Return top similar customers
        customer_similarities.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in customer_similarities[:limit]]

    def _get_products_from_similar_customers(self, similar_customers: List[int],
                                            exclude_products: set, limit: int) -> List[int]:
        from orders.models import OrderItem

        # Get products purchased by similar customers
        product_counts = defaultdict(int)
        order_items = OrderItem.objects.filter(
            order__customer_id__in=similar_customers,
            order__status='delivered'
        ).exclude(product_id__in=exclude_products).values('product_id')

        for item in order_items:
            product_counts[item['product_id']] += 1

        # Sort by frequency
        sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_products[:limit]]

# Celery task for updating recommendations
from celery import shared_task

@shared_task
def update_product_recommendations():
    """
    Periodic task to precompute recommendations
    """
    from products.models import Product
    from customers.models import Customer

    engine = RecommendationEngine()

    # Precompute content-based recommendations for all products
    products = Product.objects.filter(is_active=True).values_list('id', flat=True)
    for product_id in products:
        engine.get_content_based_recommendations(product_id)

    # Precompute personalized recommendations for active customers
    active_customers = Customer.objects.filter(
        is_active=True,
        total_orders__gt=0
    ).values_list('id', flat=True)[:1000]  # Limit to top 1000 customers

    for customer_id in active_customers:
        engine.get_personalized_recommendations(customer_id)
```

---

## 6. Key Features & API Endpoints

### DRF API Structure

```python
# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/auth/', include('api.auth_urls')),
    path('v1/payments/', include('payments.urls')),
    path('v1/recommendations/', RecommendationView.as_view()),
]

# products/serializers.py
from rest_framework import serializers
from .models import Product, ProductImage, ProductVariant

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'name', 'attributes', 'price', 'sale_price',
                  'is_active', 'image']

class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'sku', 'primary_image', 'regular_price',
                  'sale_price', 'final_price', 'rating_average', 'is_featured']

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first()
        if image:
            return self.context['request'].build_absolute_uri(image.image.url)
        return None

    def get_final_price(self, obj):
        return obj.sale_price if obj.sale_price else obj.regular_price

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

# products/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer
from recommendations.engine import RecommendationEngine

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_featured']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['created_at', 'regular_price', 'rating_average', 'sales_count']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """Get recommended products based on this product"""
        engine = RecommendationEngine()
        recommended_ids = engine.get_content_based_recommendations(int(pk))
        products = Product.objects.filter(id__in=recommended_ids)
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def track_view(self, request, pk=None):
        """Track product view for recommendations"""
        from recommendations.models import ProductInteraction
        product = self.get_object()

        ProductInteraction.objects.create(
            customer=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            product=product,
            interaction_type='view'
        )

        # Increment view count
        product.view_count += 1
        product.save(update_fields=['view_count'])

        return Response({'status': 'tracked'})
```

### Shopping Cart Implementation

```python
# cart/models.py
from django.db import models

class Cart(models.Model):
    customer = models.OneToOneField('customers.Customer', on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

# cart/services.py
from decimal import Decimal
from django.db import transaction

class CartService:
    def __init__(self, request):
        self.request = request
        self.cart = self._get_or_create_cart()

    def _get_or_create_cart(self):
        from .models import Cart

        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(customer=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(session_id=session_key)

        return cart

    @transaction.atomic
    def add_item(self, product_id: int, variant_id: int = None, quantity: int = 1):
        from .models import CartItem
        from products.models import Product, ProductVariant

        product = Product.objects.get(id=product_id)
        variant = ProductVariant.objects.get(id=variant_id) if variant_id else None

        # Check inventory
        if not self._check_inventory(product, variant, quantity):
            raise ValueError("Insufficient stock")

        cart_item, created = CartItem.objects.get_or_create(
            cart=self.cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def remove_item(self, item_id: int):
        self.cart.items.filter(id=item_id).delete()

    def update_quantity(self, item_id: int, quantity: int):
        item = self.cart.items.get(id=item_id)
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

    def get_total(self) -> Decimal:
        total = Decimal('0')
        for item in self.cart.items.select_related('product', 'variant'):
            price = item.variant.price if item.variant else item.product.regular_price
            if item.product.sale_price:
                price = item.product.sale_price
            total += price * item.quantity
        return total

    def _check_inventory(self, product, variant, quantity):
        from inventory.models import InventoryItem

        inventory = InventoryItem.objects.filter(
            product=product,
            variant=variant
        ).first()

        return inventory and inventory.quantity_available >= quantity
```

---

## 7. Solutions to Common E-Commerce Challenges

### 1. Abandoned Cart Recovery

```python
# cart/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail

@shared_task
def send_abandoned_cart_emails():
    from .models import Cart
    from customers.models import Customer

    # Find carts abandoned 2 hours ago
    cutoff_time = timezone.now() - timedelta(hours=2)
    abandoned_carts = Cart.objects.filter(
        updated_at__lte=cutoff_time,
        updated_at__gte=cutoff_time - timedelta(hours=1),
        customer__isnull=False,
        items__isnull=False
    ).distinct()

    for cart in abandoned_carts:
        if not hasattr(cart, 'recovery_email_sent'):
            send_recovery_email(cart)
            # Mark as sent (add a model field for this)

def send_recovery_email(cart):
    """Send personalized abandoned cart email"""
    # Implementation here
    pass
```

### 2. Dynamic Pricing & Promotions

```python
# promotions/models.py
from django.db import models

class Promotion(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('bogo', 'Buy One Get One'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    # Conditions
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.IntegerField(null=True, blank=True)
    max_uses_per_customer = models.IntegerField(default=1)

    # Applicability
    applies_to_products = models.ManyToManyField('products.Product', blank=True)
    applies_to_categories = models.ManyToManyField('products.Category', blank=True)

    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)
```

### 3. Fraud Detection

```python
# orders/fraud_detection.py
from typing import Dict

class FraudDetectionService:
    RISK_SCORES = {
        'high': 80,
        'medium': 50,
        'low': 20,
    }

    def calculate_risk_score(self, order_data: Dict) -> int:
        score = 0

        # Check for suspicious patterns
        if self._is_high_value_order(order_data):
            score += 20

        if self._is_new_customer(order_data):
            score += 15

        if self._shipping_billing_mismatch(order_data):
            score += 30

        if self._multiple_orders_short_time(order_data):
            score += 25

        if self._suspicious_ip(order_data):
            score += 20

        return min(score, 100)

    def get_risk_level(self, score: int) -> str:
        if score >= 70:
            return 'high'
        elif score >= 40:
            return 'medium'
        return 'low'
```

### 4. Real-time Inventory Sync

```python
# inventory/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockMovement, InventoryItem

@receiver(post_save, sender=StockMovement)
def update_inventory_on_movement(sender, instance, created, **kwargs):
    if created:
        inventory = instance.inventory_item

        if instance.movement_type in ['purchase', 'return', 'adjustment']:
            inventory.quantity_on_hand += instance.quantity
        elif instance.movement_type in ['sale', 'damage']:
            inventory.quantity_on_hand -= instance.quantity

        inventory.save()

        # Check for low stock alerts
        if inventory.quantity_on_hand <= inventory.reorder_level:
            from .tasks import create_stock_alert
            create_stock_alert.delay(inventory.id)
```

### 5. SEO Optimization

```python
# products/seo.py
from django.utils.text import slugify

def generate_meta_description(product):
    """Auto-generate SEO-friendly meta description"""
    return f"Buy {product.name} online. {product.short_description[:140]}..."

def generate_structured_data(product):
    """Generate Schema.org structured data for products"""
    return {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.name,
        "image": [product.images.first().image.url] if product.images.exists() else [],
        "description": product.description,
        "sku": product.sku,
        "brand": {
            "@type": "Brand",
            "name": product.brand.name if product.brand else ""
        },
        "offers": {
            "@type": "Offer",
            "url": f"https://example.com/products/{product.slug}",
            "priceCurrency": "USD",
            "price": str(product.sale_price or product.regular_price),
            "availability": "https://schema.org/InStock",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(product.rating_average),
            "reviewCount": str(product.rating_count)
        }
    }
```

---

## 8. Security & Performance Best Practices

### Security Checklist
1. **Multi-tenant Data Isolation**: Use django-tenants with schema separation
2. **API Authentication**: JWT tokens with refresh mechanism
3. **Rate Limiting**: Throttle API requests per tenant
4. **PCI Compliance**: Never store raw card data, use payment gateway tokens
5. **Input Validation**: Use DRF serializers with strict validation
6. **CORS Configuration**: Whitelist allowed origins per tenant
7. **SQL Injection Prevention**: Use Django ORM, never raw SQL with user input
8. **XSS Protection**: Sanitize user-generated content

### Performance Optimization
1. **Database Indexing**: Add indexes on frequently queried fields
2. **Query Optimization**: Use `select_related()` and `prefetch_related()`
3. **Caching Strategy**:
   - Redis for session storage
   - Cache product catalogs (15-30 min TTL)
   - Cache recommendations (1-2 hour TTL)
4. **CDN for Static Assets**: Use CloudFront/Cloudflare for images
5. **Database Connection Pooling**: Use pgbouncer
6. **Celery for Background Tasks**:
   - Email notifications
   - Recommendation updates
   - Report generation
   - Inventory sync

```python
# settings.py - Caching Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'update-recommendations': {
        'task': 'recommendations.tasks.update_product_recommendations',
        'schedule': 3600.0,  # Every hour
    },
    'check-low-stock': {
        'task': 'inventory.tasks.check_low_stock_alerts',
        'schedule': 1800.0,  # Every 30 minutes
    },
}
```

---

## 9. Deployment Strategy

### Infrastructure
```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: dbuser
      POSTGRES_PASSWORD: dbpassword
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A config worker -l info
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Environment Variables
```bash
# .env
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@db:5432/ecommerce
REDIS_URL=redis://redis:6379/0

# AWS/Storage
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket

# Payment Gateways
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
PAYSTACK_SECRET_KEY=sk_live_...

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

---

## Next Steps

1. **Setup Django Project**: Create project structure with multi-tenancy
2. **Database Design**: Implement all models with proper relationships
3. **API Development**: Build REST endpoints with DRF
4. **Payment Integration**: Implement Stripe and Paystack
5. **Recommendation Engine**: Deploy AI models with caching
6. **Frontend Development**: Build admin panel and customer-facing store
7. **Testing**: Write comprehensive unit and integration tests
8. **Deployment**: Deploy to AWS/DigitalOcean with Docker
9. **Monitoring**: Setup Sentry, logging, and performance monitoring
10. **Documentation**: API docs with Swagger/ReDoc

This architecture provides a solid foundation for a scalable, multi-tenant e-commerce platform that solves modern challenges like cart abandonment, fraud detection, inventory management, and personalized shopping experiences.
