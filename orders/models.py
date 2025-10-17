from django.db import models
from decimal import Decimal
import uuid

class Order(models.Model):
    """Customer orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('on_hold', 'On Hold'),
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

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, related_name='orders')

    # Guest checkout
    guest_email = models.EmailField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Currency
    currency = models.CharField(max_length=3, default='USD')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, default=1)

    # Payment
    payment_method = models.CharField(max_length=50)
    payment_gateway = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)

    # Shipping
    shipping_method = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)

    # Addresses (stored as JSON for historical accuracy)
    billing_address = models.JSONField()
    shipping_address = models.JSONField()

    # Discounts/Coupons
    coupon = models.ForeignKey('promotions.Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    gift_message = models.TextField(blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    # Flags
    is_gift = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

class OrderItem(models.Model):
    """Items within an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)

    # Product snapshot (for historical accuracy)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    variant_name = models.CharField(max_length=255, blank=True)
    product_image = models.URLField(blank=True)

    # Quantities and pricing
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Tax and discounts
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Fulfillment
    fulfilled_quantity = models.IntegerField(default=0)
    refunded_quantity = models.IntegerField(default=0)

    # Digital product
    download_url = models.URLField(blank=True)
    download_count = models.IntegerField(default=0)
    download_expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']

class ShippingZone(models.Model):
    """Shipping zones for different regions"""
    name = models.CharField(max_length=200)
    countries = models.JSONField()  # List of country codes
    states = models.JSONField(default=list)  # List of state codes
    postal_codes = models.TextField(blank=True)  # Comma-separated or ranges

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class ShippingMethod(models.Model):
    """Shipping methods for zones"""
    zone = models.ForeignKey(ShippingZone, related_name='methods', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    carrier = models.CharField(max_length=100, blank=True)

    # Delivery time
    min_delivery_days = models.IntegerField(default=1)
    max_delivery_days = models.IntegerField(default=7)
    delivery_time_description = models.CharField(max_length=200, blank=True)

    # Pricing
    PRICING_TYPES = [
        ('free', 'Free Shipping'),
        ('flat', 'Flat Rate'),
        ('weight', 'Weight Based'),
        ('price', 'Price Based'),
        ('quantity', 'Quantity Based'),
    ]
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPES, default='flat')
    flat_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Conditions
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Rates table (for weight/price based)
    rate_table = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
