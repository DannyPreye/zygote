"""
Celery Configuration for Django Multi-Tenant E-Commerce Platform
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('config')

# Load configuration from Django settings with 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


# Celery Beat Schedule - Periodic Tasks
app.conf.beat_schedule = {
    # Update product recommendations every hour
    'update-product-recommendations': {
        'task': 'recommendations.tasks.update_product_recommendations',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {'expires': 3300}  # Expire after 55 minutes
    },

    # Check low stock alerts every 30 minutes
    'check-low-stock-alerts': {
        'task': 'inventory.tasks.check_low_stock_alerts',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'options': {'expires': 1500}
    },

    # Send abandoned cart recovery emails every 2 hours
    'send-abandoned-cart-emails': {
        'task': 'cart.tasks.send_abandoned_cart_emails',
        'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
        'options': {'expires': 7000}
    },

    # Send order confirmation emails (processed immediately, but this cleans queue)
    'process-pending-emails': {
        'task': 'orders.tasks.process_pending_email_queue',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {'expires': 240}
    },

    # Update trending products cache every 15 minutes
    'update-trending-cache': {
        'task': 'recommendations.tasks.update_trending_cache',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'expires': 800}
    },

    # Check for expiring promotions daily at midnight
    'check-expiring-promotions': {
        'task': 'promotions.tasks.check_expiring_promotions',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        'options': {'expires': 3600}
    },

    # Generate daily sales report at 1 AM
    'generate-daily-sales-report': {
        'task': 'orders.tasks.generate_daily_sales_report',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
        'options': {'expires': 3600}
    },

    # Clean up expired carts weekly
    'cleanup-expired-carts': {
        'task': 'cart.tasks.cleanup_expired_carts',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday at 2 AM
        'options': {'expires': 3600}
    },

    # Update customer segments monthly
    'update-customer-segments': {
        'task': 'customers.tasks.update_customer_segments',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 1st of month at 3 AM
        'options': {'expires': 7200}
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery is working."""
    print(f'Request: {self.request!r}')

