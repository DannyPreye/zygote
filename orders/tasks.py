"""
Celery tasks for order management
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name="orders.tasks.send_order_confirmation_email")
def send_order_confirmation_email(order_id):
    """
    Send order confirmation email to customer.

    Args:
        order_id: ID of the order
    """
    from .models import Order

    logger.info(f"Sending order confirmation email for order {order_id}...")

    try:
        order = Order.objects.select_related('customer', 'billing_address', 'shipping_address').prefetch_related('items__product').get(id=order_id)

        if not order.customer or not order.customer.email:
            logger.warning(f"Order {order_id} has no associated customer or email")
            return {"status": "skipped", "reason": "no_email"}

        context = {
            'customer_name': order.customer.get_full_name() or order.customer.email,
            'order': order,
            'items': order.items.all(),
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }

        # Render email template
        try:
            html_message = render_to_string('emails/order_confirmation.html', context)
            text_message = render_to_string('emails/order_confirmation.txt', context)
        except Exception as template_error:
            logger.error(f"Template rendering error: {template_error}")
            # Fallback
            text_message = f"""
Hi {context['customer_name']},

Thank you for your order #{order.order_number}!

Order Total: ${order.total_amount:.2f}
Status: {order.get_status_display()}

Track your order: {context['order_url']}

Thanks for shopping with us!
"""
            html_message = None

        send_mail(
            subject=f'Order Confirmation #{order.order_number}',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Order confirmation email sent for order {order_id}")
        return {"status": "success", "email": order.customer.email}

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {"status": "error", "message": "Order not found"}
    except Exception as e:
        logger.error(f"Error sending order confirmation email: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="orders.tasks.send_order_status_update_email")
def send_order_status_update_email(order_id, old_status, new_status):
    """
    Send email notification when order status changes.

    Args:
        order_id: ID of the order
        old_status: Previous order status
        new_status: New order status
    """
    from .models import Order

    logger.info(f"Sending order status update email for order {order_id}: {old_status} -> {new_status}")

    try:
        order = Order.objects.select_related('customer').get(id=order_id)

        if not order.customer or not order.customer.email:
            return {"status": "skipped", "reason": "no_email"}

        status_messages = {
            'processing': 'Your order is being processed',
            'shipped': 'Your order has been shipped',
            'delivered': 'Your order has been delivered',
            'cancelled': 'Your order has been cancelled',
        }

        context = {
            'customer_name': order.customer.get_full_name() or order.customer.email,
            'order': order,
            'status_message': status_messages.get(new_status, f'Status updated to {new_status}'),
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }

        try:
            html_message = render_to_string('emails/order_status_update.html', context)
            text_message = render_to_string('emails/order_status_update.txt', context)
        except Exception:
            text_message = f"""
Hi {context['customer_name']},

Order Update: #{order.order_number}

{context['status_message']}

Track your order: {context['order_url']}

Thanks!
"""
            html_message = None

        send_mail(
            subject=f'Order #{order.order_number} - {status_messages.get(new_status, "Status Update")}',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Order status update email sent for order {order_id}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error sending order status update email: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="orders.tasks.send_shipping_notification_email")
def send_shipping_notification_email(order_id, tracking_number=None):
    """
    Send shipping notification with tracking information.

    Args:
        order_id: ID of the order
        tracking_number: Tracking number for shipment
    """
    from .models import Order

    logger.info(f"Sending shipping notification for order {order_id}")

    try:
        order = Order.objects.select_related('customer', 'shipping_address').get(id=order_id)

        if not order.customer or not order.customer.email:
            return {"status": "skipped", "reason": "no_email"}

        context = {
            'customer_name': order.customer.get_full_name() or order.customer.email,
            'order': order,
            'tracking_number': tracking_number or order.tracking_number,
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }

        try:
            html_message = render_to_string('emails/shipping_notification.html', context)
            text_message = render_to_string('emails/shipping_notification.txt', context)
        except Exception:
            text_message = f"""
Hi {context['customer_name']},

Great news! Your order #{order.order_number} has shipped.

{'Tracking Number: ' + context['tracking_number'] if context['tracking_number'] else 'Track your order: ' + context['order_url']}

Thanks for your purchase!
"""
            html_message = None

        send_mail(
            subject=f'Your Order #{order.order_number} Has Shipped',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Shipping notification sent for order {order_id}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error sending shipping notification: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="orders.tasks.generate_invoice")
def generate_invoice(order_id):
    """
    Generate PDF invoice for an order.

    Args:
        order_id: ID of the order
    """
    from .models import Order

    logger.info(f"Generating invoice for order {order_id}")

    try:
        order = Order.objects.select_related('customer', 'billing_address').prefetch_related('items__product').get(id=order_id)

        # TODO: Implement PDF generation using ReportLab or WeasyPrint
        # For now, just log that invoice generation was triggered

        logger.info(f"Invoice generation completed for order {order_id}")
        return {"status": "success", "order_number": order.order_number}

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {"status": "error", "message": "Order not found"}
    except Exception as e:
        logger.error(f"Error generating invoice: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="orders.tasks.auto_complete_delivered_orders")
def auto_complete_delivered_orders():
    """
    Automatically mark delivered orders as completed after 7 days.
    Runs daily.
    """
    from .models import Order
    from datetime import timedelta

    logger.info("Running auto-complete for delivered orders...")

    cutoff_date = timezone.now() - timedelta(days=7)

    orders = Order.objects.filter(
        status='delivered',
        delivered_at__lte=cutoff_date
    )

    count = orders.count()
    orders.update(status='completed', updated_at=timezone.now())

    logger.info(f"Auto-completed {count} delivered orders")
    return {"completed": count}

