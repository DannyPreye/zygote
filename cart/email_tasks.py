"""
Email notification tasks for cart
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(name="cart.email_tasks.send_abandoned_cart_email")
def send_abandoned_cart_email(cart_id):
    """
    Send abandoned cart reminder email to customer.

    Args:
        cart_id: ID of the abandoned cart
    """
    from .models import Cart

    logger.info(f"Sending abandoned cart email for cart {cart_id}...")

    try:
        cart = Cart.objects.get(id=cart_id)

        if not cart.user or not cart.user.email:
            logger.warning(f"Cart {cart_id} has no associated user or email")
            return {"status": "skipped", "reason": "no_email"}

        # Calculate cart summary
        items = cart.items.select_related('product').all()
        if not items:
            logger.warning(f"Cart {cart_id} has no items")
            return {"status": "skipped", "reason": "no_items"}

        total = sum(item.subtotal for item in items)

        # Prepare email context
        context = {
            'customer_name': cart.user.get_full_name() or cart.user.email,
            'cart': cart,
            'items': items,
            'total': total,
            'cart_url': f"{settings.FRONTEND_URL}/cart",
        }

        # Render email template
        try:
            html_message = render_to_string('emails/abandoned_cart.html', context)
            text_message = render_to_string('emails/abandoned_cart.txt', context)
        except Exception as template_error:
            logger.error(f"Template rendering error: {template_error}")
            # Fallback to simple text email
            text_message = f"""
Hi {context['customer_name']},

You left {len(items)} item(s) in your cart worth ${total:.2f}.

Complete your purchase now: {context['cart_url']}

Thanks,
The Team
"""
            html_message = None

        # Send email
        send_mail(
            subject='You left items in your cart',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cart.user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Abandoned cart email sent successfully for cart {cart_id}")
        return {"status": "success", "email": cart.user.email}

    except Cart.DoesNotExist:
        logger.error(f"Cart {cart_id} not found")
        return {"status": "error", "message": "Cart not found"}
    except Exception as e:
        logger.error(f"Error sending abandoned cart email for cart {cart_id}: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="cart.email_tasks.send_back_in_stock_notification")
def send_back_in_stock_notification(product_id, customer_ids):
    """
    Notify customers when a product is back in stock.

    Args:
        product_id: ID of the product that's back in stock
        customer_ids: List of customer IDs to notify
    """
    from products.models import Product
    from customers.models import Customer

    logger.info(f"Sending back-in-stock notifications for product {product_id} to {len(customer_ids)} customers...")

    try:
        product = Product.objects.get(id=product_id)
        customers = Customer.objects.filter(id__in=customer_ids, email__isnull=False)

        sent_count = 0
        for customer in customers:
            try:
                context = {
                    'customer_name': customer.get_full_name() or customer.email,
                    'product': product,
                    'product_url': f"{settings.FRONTEND_URL}/products/{product.slug}",
                }

                # Render email template
                try:
                    html_message = render_to_string('emails/back_in_stock.html', context)
                    text_message = render_to_string('emails/back_in_stock.txt', context)
                except Exception:
                    # Fallback
                    text_message = f"""
Hi {context['customer_name']},

Good news! {product.name} is back in stock.

View it now: {context['product_url']}

Thanks,
The Team
"""
                    html_message = None

                send_mail(
                    subject=f'{product.name} is back in stock!',
                    message=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                sent_count += 1

            except Exception as e:
                logger.error(f"Error sending back-in-stock email to customer {customer.id}: {e}")
                continue

        logger.info(f"Back-in-stock notifications sent: {sent_count}/{len(customer_ids)}")
        return {"status": "success", "sent": sent_count, "total": len(customer_ids)}

    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found")
        return {"status": "error", "message": "Product not found"}
    except Exception as e:
        logger.error(f"Error in back-in-stock notification task: {e}")
        return {"status": "error", "message": str(e)}

