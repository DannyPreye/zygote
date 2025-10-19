"""
Stripe Payment Gateway Implementation
"""
import stripe
from decimal import Decimal
from typing import Dict, Any
import logging

from .base import PaymentGateway, PaymentGatewayError

logger = logging.getLogger(__name__)


class StripeGateway(PaymentGateway):
    """
    Stripe payment gateway implementation.

    Handles payment processing through Stripe API.
    Documentation: https://stripe.com/docs/api
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize Stripe gateway.

        Args:
            api_key: Stripe secret key (sk_test_... or sk_live_...)
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        stripe.api_key = api_key
        self.gateway_name = 'stripe'

    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Stripe PaymentIntent.

        Args:
            amount: Payment amount in major currency unit (e.g., 10.50 USD)
            currency: Currency code (usd, eur, gbp, etc.)
            metadata: Additional metadata for the payment

        Returns:
            Dict with payment intent details
        """
        try:
            # Convert amount to cents (Stripe uses smallest currency unit)
            amount_cents = int(amount * 100)

            # Create PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=metadata,
                automatic_payment_methods={'enabled': True},
                description=f"Order #{metadata.get('order_number', 'N/A')}"
            )

            logger.info(f"Stripe PaymentIntent created: {intent.id}")

            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'amount': float(amount),
                'currency': currency,
                'created': intent.created,
                'payment_method_types': intent.payment_method_types,
            }

        except stripe.error.CardError as e:
            # Card was declined
            error_msg = e.user_message or str(e)
            logger.error(f"Stripe card error: {error_msg}")
            raise PaymentGatewayError(
                message=error_msg,
                gateway=self.gateway_name,
                error_code=e.code,
                details={'type': 'card_error', 'param': e.param}
            )

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters
            logger.error(f"Stripe invalid request: {str(e)}")
            raise PaymentGatewayError(
                message="Invalid payment request",
                gateway=self.gateway_name,
                error_code='invalid_request',
                details={'error': str(e)}
            )

        except stripe.error.AuthenticationError as e:
            # Authentication failed
            logger.error(f"Stripe authentication error: {str(e)}")
            raise PaymentGatewayError(
                message="Payment gateway authentication failed",
                gateway=self.gateway_name,
                error_code='authentication_error'
            )

        except stripe.error.APIConnectionError as e:
            # Network error
            logger.error(f"Stripe connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Payment gateway connection failed",
                gateway=self.gateway_name,
                error_code='connection_error'
            )

        except stripe.error.StripeError as e:
            # Generic Stripe error
            logger.error(f"Stripe error: {str(e)}")
            raise PaymentGatewayError(
                message="Payment processing failed",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

        except Exception as e:
            logger.error(f"Unexpected error in Stripe gateway: {str(e)}")
            raise PaymentGatewayError(
                message="An unexpected error occurred",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Retrieve and confirm a Stripe PaymentIntent.

        Args:
            payment_intent_id: The PaymentIntent ID (pi_...)

        Returns:
            Dict with payment details and status
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Extract card details if available
            card_details = {}
            if intent.charges and intent.charges.data:
                charge = intent.charges.data[0]
                if charge.payment_method_details and charge.payment_method_details.card:
                    card = charge.payment_method_details.card
                    card_details = {
                        'card_last4': card.last4,
                        'card_brand': card.brand,
                        'card_exp_month': card.exp_month,
                        'card_exp_year': card.exp_year,
                    }

            return {
                'id': intent.id,
                'status': intent.status,  # succeeded, processing, requires_payment_method, etc.
                'amount': Decimal(intent.amount) / 100,
                'currency': intent.currency,
                'created': intent.created,
                'payment_method': intent.payment_method,
                **card_details,
                'metadata': intent.metadata,
            }

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe payment not found: {payment_intent_id}")
            raise PaymentGatewayError(
                message="Payment not found",
                gateway=self.gateway_name,
                error_code='not_found',
                details={'payment_id': payment_intent_id}
            )

        except Exception as e:
            logger.error(f"Error confirming Stripe payment: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to confirm payment",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def create_refund(self, payment_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Create a refund for a Stripe payment.

        Args:
            payment_id: The PaymentIntent ID
            amount: Refund amount in major currency unit

        Returns:
            Dict with refund details
        """
        try:
            # Convert amount to cents
            amount_cents = int(amount * 100) if amount else None

            refund_params = {
                'payment_intent': payment_id,
            }

            if amount_cents:
                refund_params['amount'] = amount_cents

            refund = stripe.Refund.create(**refund_params)

            logger.info(f"Stripe refund created: {refund.id} for payment {payment_id}")

            return {
                'id': refund.id,
                'status': refund.status,  # succeeded, pending, failed
                'amount': Decimal(refund.amount) / 100,
                'currency': refund.currency,
                'payment_intent': refund.payment_intent,
                'reason': refund.reason,
                'created': refund.created,
            }

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe refund error: {str(e)}")
            raise PaymentGatewayError(
                message="Refund request failed",
                gateway=self.gateway_name,
                error_code='invalid_refund',
                details={'error': str(e)}
            )

        except Exception as e:
            logger.error(f"Error creating Stripe refund: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to create refund",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str = None) -> bool:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value
            webhook_secret: Webhook signing secret (whsec_...)

        Returns:
            bool: True if signature is valid
        """
        if not webhook_secret:
            logger.warning("Stripe webhook secret not provided")
            return False

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            logger.info(f"Stripe webhook verified: {event.type}")
            return True

        except ValueError:
            # Invalid payload
            logger.error("Stripe webhook: Invalid payload")
            return False

        except stripe.error.SignatureVerificationError:
            # Invalid signature
            logger.error("Stripe webhook: Invalid signature")
            return False

        except Exception as e:
            logger.error(f"Stripe webhook verification error: {str(e)}")
            return False

    def get_webhook_event(self, payload: bytes, signature: str, webhook_secret: str) -> Dict[str, Any]:
        """
        Parse and return Stripe webhook event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            webhook_secret: Webhook signing secret

        Returns:
            Dict with event data
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return {
                'id': event.id,
                'type': event.type,
                'data': event.data.to_dict(),
                'created': event.created,
            }
        except Exception as e:
            logger.error(f"Error parsing Stripe webhook: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to parse webhook",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

