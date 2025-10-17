"""
Payment Gateway Factory
"""
from django.conf import settings


def get_gateway(gateway_name):
    """
    Factory function to get payment gateway instance.

    Args:
        gateway_name: Name of the gateway ('stripe', 'paystack', 'paypal')

    Returns:
        Gateway instance

    Raises:
        ValueError: If gateway name is not supported
    """
    gateway_name = gateway_name.lower()

    if gateway_name == 'stripe':
        from .stripe_gateway import StripeGateway
        api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        return StripeGateway(api_key)

    elif gateway_name == 'paystack':
        from .paystack_gateway import PaystackGateway
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        return PaystackGateway(secret_key)

    elif gateway_name == 'paypal':
        from .paypal_gateway import PayPalGateway
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        return PayPalGateway(client_id, client_secret)

    else:
        raise ValueError(f"Unsupported payment gateway: {gateway_name}")


__all__ = ['get_gateway']

