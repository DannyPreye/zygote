"""
Celery tasks for customer management
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(name="customers.tasks.send_welcome_email")
def send_welcome_email(customer_id):
    """
    Send welcome email to new customer.

    Args:
        customer_id: ID of the customer
    """
    from .models import Customer

    logger.info(f"Sending welcome email to customer {customer_id}...")

    try:
        customer = Customer.objects.get(id=customer_id)

        if not customer.email:
            logger.warning(f"Customer {customer_id} has no email")
            return {"status": "skipped", "reason": "no_email"}

        context = {
            'customer_name': customer.get_full_name() or customer.email,
            'customer': customer,
            'site_url': settings.FRONTEND_URL,
        }

        try:
            html_message = render_to_string('emails/welcome.html', context)
            text_message = render_to_string('emails/welcome.txt', context)
        except Exception:
            text_message = f"""
Hi {context['customer_name']},

Welcome to our store!

We're excited to have you as a customer. Start exploring our products: {context['site_url']}

Thanks for joining us!
"""
            html_message = None

        send_mail(
            subject='Welcome to Our Store!',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Welcome email sent to customer {customer_id}")
        return {"status": "success", "email": customer.email}

    except Customer.DoesNotExist:
        logger.error(f"Customer {customer_id} not found")
        return {"status": "error", "message": "Customer not found"}
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="customers.tasks.send_password_reset_email")
def send_password_reset_email(customer_id, reset_token):
    """
    Send password reset email.

    Args:
        customer_id: ID of the customer
        reset_token: Password reset token
    """
    from .models import Customer

    logger.info(f"Sending password reset email to customer {customer_id}...")

    try:
        customer = Customer.objects.get(id=customer_id)

        if not customer.email:
            return {"status": "skipped", "reason": "no_email"}

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        context = {
            'customer_name': customer.get_full_name() or customer.email,
            'reset_url': reset_url,
        }

        try:
            html_message = render_to_string('emails/password_reset.html', context)
            text_message = render_to_string('emails/password_reset.txt', context)
        except Exception:
            text_message = f"""
Hi {context['customer_name']},

You requested a password reset.

Reset your password: {reset_url}

This link expires in 1 hour.

If you didn't request this, please ignore this email.
"""
            html_message = None

        send_mail(
            subject='Password Reset Request',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to customer {customer_id}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="customers.tasks.send_email_verification")
def send_email_verification(customer_id, verification_token):
    """
    Send email verification link.

    Args:
        customer_id: ID of the customer
        verification_token: Email verification token
    """
    from .models import Customer

    logger.info(f"Sending email verification to customer {customer_id}...")

    try:
        customer = Customer.objects.get(id=customer_id)

        if not customer.email:
            return {"status": "skipped", "reason": "no_email"}

        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

        context = {
            'customer_name': customer.get_full_name() or customer.email,
            'verification_url': verification_url,
        }

        try:
            html_message = render_to_string('emails/email_verification.html', context)
            text_message = render_to_string('emails/email_verification.txt', context)
        except Exception:
            text_message = f"""
Hi {context['customer_name']},

Please verify your email address to activate your account.

Verify email: {verification_url}

Thanks!
"""
            html_message = None

        send_mail(
            subject='Please Verify Your Email',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Email verification sent to customer {customer_id}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error sending email verification: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="customers.tasks.send_promotional_email")
def send_promotional_email(customer_ids, subject, message, html_content=None):
    """
    Send promotional email to multiple customers.

    Args:
        customer_ids: List of customer IDs
        subject: Email subject
        message: Plain text message
        html_content: Optional HTML content
    """
    from .models import Customer

    logger.info(f"Sending promotional email to {len(customer_ids)} customers...")

    customers = Customer.objects.filter(id__in=customer_ids, email__isnull=False)

    sent_count = 0
    for customer in customers:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.email],
                html_message=html_content,
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending promotional email to customer {customer.id}: {e}")
            continue

    logger.info(f"Promotional emails sent: {sent_count}/{len(customer_ids)}")
    return {"status": "success", "sent": sent_count, "total": len(customer_ids)}

