from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid

User = get_user_model()

class Warehouse(models.Model):
    """Warehouse/Storage location management"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    # Contact
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    can_ship = models.BooleanField(default=True)
    can_receive = models.BooleanField(default=True)

    # Capacity
    max_capacity = models.IntegerField(null=True, blank=True)
    current_capacity = models.IntegerField(default=0)

    # Operating hours
    operating_hours = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class InventoryItem(models.Model):
    """Stock levels for products in warehouses"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)

    # Stock Levels
    quantity_on_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_reserved = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_available = models.IntegerField(default=0)
    quantity_incoming = models.IntegerField(default=0)  # From purchase orders

    # Reorder Settings
    reorder_level = models.IntegerField(default=10)
    reorder_quantity = models.IntegerField(default=50)
    max_stock_level = models.IntegerField(null=True, blank=True)

    # Location in Warehouse
    bin_location = models.CharField(max_length=50, blank=True)
    aisle = models.CharField(max_length=20, blank=True)
    shelf = models.CharField(max_length=20, blank=True)

    # Tracking
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    last_counted_at = models.DateTimeField(null=True, blank=True)
    last_restocked_at = models.DateTimeField(null=True, blank=True)

    # Cost
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['product', 'variant', 'warehouse']]
        indexes = [
            models.Index(fields=['product', 'warehouse']),
            models.Index(fields=['quantity_available']),
        ]

    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)

class StockMovement(models.Model):
    """Track all inventory movements"""
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase/Restock'),
        ('sale', 'Sale'),
        ('return', 'Customer Return'),
        ('adjustment', 'Inventory Adjustment'),
        ('damage', 'Damage/Loss'),
        ('transfer', 'Warehouse Transfer'),
        ('manufacturing', 'Manufacturing'),
        ('reservation', 'Reservation'),
        ('release', 'Release Reservation'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()  # Positive for incoming, negative for outgoing

    # References
    reference_type = models.CharField(max_length=50, blank=True)  # 'order', 'purchase_order', etc
    reference_id = models.IntegerField(null=True, blank=True)

    # Transfer details
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True,
                                       related_name='outgoing_transfers', blank=True)
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True,
                                     related_name='incoming_transfers', blank=True)

    # Cost tracking
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class StockAlert(models.Model):
    """Inventory alerts"""
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('overstock', 'Overstock'),
        ('expiring_soon', 'Expiring Soon'),
    ]

    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold_value = models.IntegerField(null=True, blank=True)
    current_value = models.IntegerField(null=True, blank=True)

    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Supplier(models.Model):
    """Supplier management"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)

    # Contact
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    # Business details
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    lead_time_days = models.IntegerField(default=0)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Rating
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    """Purchase orders for inventory restocking"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, related_name='purchase_orders')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Dates
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment
    payment_status = models.CharField(max_length=20, default='pending')
    payment_terms = models.CharField(max_length=200, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class PurchaseOrderItem(models.Model):
    """Items in a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, null=True, blank=True)

    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)

    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True)
