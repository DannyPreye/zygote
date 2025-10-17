from django.db import models
import uuid

class Promotion(models.Model):
    """Promotional campaigns"""
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage Off'),
        ('fixed', 'Fixed Amount Off'),
        ('bogo', 'Buy One Get One'),
        ('bundle', 'Bundle Deal'),
        ('free_shipping', 'Free Shipping'),
    ]

    APPLY_TO = [
        ('all', 'All Products'),
        ('specific_products', 'Specific Products'),
        ('specific_categories', 'Specific Categories'),
        ('specific_brands', 'Specific Brands'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Discount
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    # Application
    apply_to = models.CharField(max_length=30, choices=APPLY_TO, default='all')
    products = models.ManyToManyField('products.Product', blank=True)
    categories = models.ManyToManyField('products.Category', blank=True)
    brands = models.ManyToManyField('products.Brand', blank=True)

    # Conditions
    min_quantity = models.IntegerField(null=True, blank=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Customer targeting
    customer_groups = models.ManyToManyField('customers.CustomerGroup', blank=True)

    # Usage limits
    max_uses = models.IntegerField(null=True, blank=True)
    max_uses_per_customer = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)

    # Dates
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Display
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']

class Coupon(models.Model):
    """Discount coupons"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='coupons')

    # Additional restrictions
    is_single_use = models.BooleanField(default=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)

    # Usage tracking
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='used_coupons')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class CouponUsage(models.Model):
    """Track coupon usage"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usage_history')
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)

    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['coupon', 'order']]
