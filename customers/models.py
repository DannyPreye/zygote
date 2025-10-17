from django.contrib.auth.models import AbstractUser, Group
from django.db import models
import uuid
class Customer(AbstractUser):
    # Fix clash with AbstractUser's groups and user_permissions
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="customer_set",
        related_query_name="customer",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customer_set",
        related_query_name="customer",
    )
    """Extended user model for customers"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Personal info
    phone = models.CharField(max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)

    # Avatar
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Marketing
    accepts_marketing_email = models.BooleanField(default=False)
    accepts_marketing_sms = models.BooleanField(default=False)

    # Customer stats (denormalized)
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_order_date = models.DateTimeField(null=True, blank=True)

    # Loyalty
    loyalty_points = models.IntegerField(default=0)
    loyalty_tier = models.CharField(max_length=50, default='bronze')

    # Customer segments (renamed from groups to avoid clash with auth.User.groups)
    customer_groups = models.ManyToManyField('CustomerGroup', blank=True, related_name='customers')

    # Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    preferred_currency = models.CharField(max_length=3, default='USD')

    # Metadata
    source = models.CharField(max_length=100, blank=True)  # How they found us
    referrer = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    # Status
    is_verified = models.BooleanField(default=False)
    is_vip = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
        ]

class CustomerGroup(models.Model):
    """Customer segmentation groups"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Automatic assignment rules
    auto_assign = models.BooleanField(default=False)
    assignment_rules = models.JSONField(default=dict, blank=True)

    # Perks
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    priority_support = models.BooleanField(default=False)
    free_shipping = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Address(models.Model):
    """Customer addresses"""
    ADDRESS_TYPES = [
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
    ]

    customer = models.ForeignKey(Customer, related_name='addresses', on_delete=models.CASCADE)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)

    # Name
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company = models.CharField(max_length=200, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    # Contact
    phone = models.CharField(max_length=20)

    # Flags
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
