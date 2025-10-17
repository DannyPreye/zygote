from django.db import models

class ProductInteraction(models.Model):
    """Track user interactions with products"""
    INTERACTION_TYPES = [
        ('view', 'View'),
        ('click', 'Click'),
        ('cart', 'Add to Cart'),
        ('wishlist', 'Add to Wishlist'),
        ('purchase', 'Purchase'),
        ('review', 'Review'),
        ('share', 'Share'),
        ('search', 'Search Result Click'),
    ]

    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)

    # Context
    source = models.CharField(max_length=50, blank=True)  # homepage, search, category, etc
    search_query = models.CharField(max_length=500, blank=True)
    referrer_url = models.URLField(blank=True)

    # Interaction details
    duration_seconds = models.IntegerField(null=True, blank=True)  # For view interactions
    position = models.IntegerField(null=True, blank=True)  # Position in list

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['product', 'interaction_type']),
            models.Index(fields=['session_id', '-created_at']),
        ]
        ordering = ['-created_at']

class RecommendationLog(models.Model):
    """Log recommendations shown to users"""
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255)

    recommendation_type = models.CharField(max_length=50)  # collaborative, content, trending
    recommended_products = models.JSONField()  # List of product IDs

    # Context
    source_product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True)
    page_type = models.CharField(max_length=50)  # homepage, product, cart

    # Performance
    clicked_products = models.JSONField(default=list)
    conversion = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['session_id', '-created_at']),
        ]
