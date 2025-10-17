from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.postgres.fields import ArrayField
import uuid

class Tenant(TenantMixin):
    """Multi-tenant model for store isolation"""

    # Basic Information
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=50)
    schema_name = models.CharField(max_length=63, unique=True)

    # Business Details
    business_name = models.CharField(max_length=255)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=20)
    business_address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)

    # Subscription & Billing
    SUBSCRIPTION_PLANS = [
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    subscription_plan = models.CharField(max_length=50, choices=SUBSCRIPTION_PLANS, default='trial')
    subscription_status = models.CharField(max_length=20, default='active')
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)

    # Configuration
    currency = models.CharField(max_length=3, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    country = models.CharField(max_length=2, default='US')

    # Branding
    logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)
    favicon = models.ImageField(upload_to='tenant_favicons/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#000000')
    secondary_color = models.CharField(max_length=7, default='#ffffff')

    # Feature Flags
    features = models.JSONField(default=dict)
    max_products = models.IntegerField(default=1000)
    max_users = models.IntegerField(default=10)

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Settings
    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        ordering = ['-created_on']

    def __str__(self):
        return self.business_name

class Domain(DomainMixin):
    """Domain model for tenant routing"""
    is_ssl = models.BooleanField(default=False)
    ssl_certificate = models.TextField(blank=True)

    class Meta:
        ordering = ['domain']
