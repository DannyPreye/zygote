from django.db import models
import uuid
from django.core.validators import MinValueValidator

class Cart(models.Model):
    """Shopping cart"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.OneToOneField('customers.Customer', on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)

    # For abandoned cart recovery
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Recovery
    abandoned_email_sent = models.BooleanField(default=False)
    abandoned_email_sent_at = models.DateTimeField(null=True, blank=True)
    recovered = models.BooleanField(default=False)
    recovered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['customer']),
        ]

class CartItem(models.Model):
    """Items in cart"""
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)

    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Price snapshot
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Personalization
    personalization = models.JSONField(default=dict, blank=True)  # Custom text, options

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['cart', 'product', 'variant']]
        ordering = ['-added_at']

class Wishlist(models.Model):
    """Customer wishlist"""
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=200, default='My Wishlist')
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

class WishlistItem(models.Model):
    """Items in wishlist"""
    wishlist = models.ForeignKey(Wishlist, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)

    note = models.TextField(blank=True)
    priority = models.IntegerField(default=0)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['wishlist', 'product', 'variant']]
        ordering = ['-priority', '-added_at']



