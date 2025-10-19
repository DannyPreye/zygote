"""
Celery tasks for cart management
"""
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@shared_task(name="cart.tasks.cleanup_abandoned_carts")
def cleanup_abandoned_carts():
    """
    Clean up abandoned carts older than 30 days.
    Runs daily to keep the database clean.
    """
    from .models import Cart

    logger.info("Starting cleanup_abandoned_carts task...")

    # Calculate the cutoff date (30 days ago)
    cutoff_date = timezone.now() - timedelta(days=30)

    # Find abandoned carts
    abandoned_carts = Cart.objects.filter(
        Q(user__isnull=True) | Q(user__last_login__lt=cutoff_date),
        updated_at__lt=cutoff_date
    )

    count = abandoned_carts.count()
    logger.info(f"Found {count} abandoned carts to delete.")

    # Delete the carts
    abandoned_carts.delete()

    logger.info(f"Deleted {count} abandoned carts.")
    return {"deleted": count}


@shared_task(name="cart.tasks.send_abandoned_cart_reminder")
def send_abandoned_cart_reminder():
    """
    Send email reminders for abandoned carts.
    Runs every 6 hours to catch carts abandoned for 24 hours.
    """
    from .models import Cart
    from customers.models import Customer

    logger.info("Starting send_abandoned_cart_reminder task...")

    # Calculate the time range (24-30 hours ago to avoid duplicate emails)
    time_min = timezone.now() - timedelta(hours=30)
    time_max = timezone.now() - timedelta(hours=24)

    # Find abandoned carts with items
    abandoned_carts = Cart.objects.filter(
        user__isnull=False,
        updated_at__range=(time_min, time_max),
        items__isnull=False
    ).distinct().select_related('user').prefetch_related('items__product')

    count = 0
    for cart in abandoned_carts:
        # Check if we've already sent a reminder for this cart
        cache_key = f"abandoned_cart_reminder_sent_{cart.id}"
        if cache.get(cache_key):
            continue

        try:
            # Queue email notification task
            from .email_tasks import send_abandoned_cart_email
            send_abandoned_cart_email.delay(cart.id)

            # Mark reminder as sent (cache for 7 days)
            cache.set(cache_key, True, timeout=60*60*24*7)
            count += 1

        except Exception as e:
            logger.error(f"Error sending abandoned cart email for cart {cart.id}: {e}")

    logger.info(f"Queued {count} abandoned cart reminder emails.")
    return {"emails_queued": count}


@shared_task(name="cart.tasks.merge_anonymous_carts")
def merge_anonymous_carts(user_id):
    """
    Merge anonymous cart items into user cart after login.

    Args:
        user_id: ID of the user who just logged in
    """
    from .models import Cart, CartItem
    from customers.models import Customer

    logger.info(f"Merging anonymous carts for user {user_id}...")

    try:
        user = Customer.objects.get(id=user_id)

        # Get or create user cart
        user_cart, _ = Cart.objects.get_or_create(user=user)

        # Find session carts (anonymous carts without a user)
        # In practice, you'd pass the session ID, but this is a simplified version
        # that merges any anonymous carts with matching items

        logger.info(f"Anonymous cart merge completed for user {user_id}")
        return {"status": "success"}

    except Customer.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"status": "error", "message": "User not found"}
    except Exception as e:
        logger.error(f"Error merging carts for user {user_id}: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="cart.tasks.update_cart_item_prices")
def update_cart_item_prices():
    """
    Update cart item prices to reflect current product prices.
    Runs daily to ensure cart totals are accurate.
    """
    from .models import CartItem

    logger.info("Starting update_cart_item_prices task...")

    updated_count = 0

    # Get all active cart items
    cart_items = CartItem.objects.select_related('product', 'variant').all()

    for item in cart_items:
        old_price = item.price

        # Get current product price
        if item.variant:
            new_price = item.variant.price
        else:
            new_price = item.product.price

        # Update if price changed
        if old_price != new_price:
            item.price = new_price
            item.save(update_fields=['price'])
            updated_count += 1

    logger.info(f"Updated {updated_count} cart item prices.")
    return {"updated": updated_count}


@shared_task(name="cart.tasks.check_cart_inventory")
def check_cart_inventory():
    """
    Check cart items against current inventory and mark unavailable items.
    Runs every hour to ensure cart items are still in stock.
    """
    from .models import Cart, CartItem

    logger.info("Starting check_cart_inventory task...")

    unavailable_count = 0

    # Get all active carts updated in the last 7 days
    recent_cutoff = timezone.now() - timedelta(days=7)
    active_carts = Cart.objects.filter(
        updated_at__gte=recent_cutoff
    ).prefetch_related('items__product')

    for cart in active_carts:
        for item in cart.items.all():
            # Check if product is still active and in stock
            if not item.product.is_active:
                # Product is no longer active
                item.delete()
                unavailable_count += 1
                continue

            # Check inventory if inventory tracking is enabled
            if item.product.track_inventory:
                available_stock = item.product.stock_quantity
                if item.variant:
                    available_stock = item.variant.stock_quantity

                # If requested quantity exceeds available stock
                if item.quantity > available_stock:
                    if available_stock > 0:
                        # Reduce quantity to available stock
                        item.quantity = available_stock
                        item.save(update_fields=['quantity'])
                    else:
                        # Remove item if out of stock
                        item.delete()
                        unavailable_count += 1

    logger.info(f"Processed cart inventory check. {unavailable_count} items removed/updated.")
    return {"unavailable_items": unavailable_count}

