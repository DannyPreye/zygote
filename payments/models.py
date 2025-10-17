from django.db import models
import uuid

class Payment(models.Model):
    """Payment transactions"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order = models.ForeignKey('orders.Order', related_name='payments', on_delete=models.CASCADE)

    # Gateway info
    gateway = models.CharField(max_length=50)  # stripe, paystack, paypal
    payment_method = models.CharField(max_length=50)  # card, bank_transfer, wallet

    # Amounts
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)

    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Gateway response
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    gateway_response = models.JSONField(default=dict)

    # Card details (tokenized)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)

    # Metadata
    customer_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Error handling
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['order', 'status']),
        ]

class Refund(models.Model):
    """Payment refunds"""
    REFUND_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    REFUND_REASONS = [
        ('duplicate', 'Duplicate Payment'),
        ('fraudulent', 'Fraudulent'),
        ('requested', 'Customer Requested'),
        ('product_issue', 'Product Issue'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment = models.ForeignKey(Payment, related_name='refunds', on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REFUND_REASONS)
    notes = models.TextField(blank=True)

    # Gateway
    refund_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    gateway_response = models.JSONField(default=dict)

    created_by = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
