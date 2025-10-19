"""
Paystack Payment Gateway Implementation
"""
from decimal import Decimal
from typing import Dict, Any
import logging
import requests
import hmac
import hashlib

from .base import PaymentGateway, PaymentGatewayError

logger = logging.getLogger(__name__)


class PaystackGateway(PaymentGateway):
    """
    Paystack payment gateway implementation.

    Handles payment processing through Paystack API (African payments).
    Documentation: https://paystack.com/docs/api
    """

    BASE_URL = "https://api.paystack.co"

    def __init__(self, secret_key: str, **kwargs):
        """
        Initialize Paystack gateway.

        Args:
            secret_key: Paystack secret key (sk_test_... or sk_live_...)
            **kwargs: Additional configuration
        """
        super().__init__(secret_key, **kwargs)
        self.secret_key = secret_key
        self.gateway_name = 'paystack'
        self.headers = {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json'
        }

    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction.

        Args:
            amount: Payment amount in major currency unit
            currency: Currency code (NGN, GHS, ZAR, USD)
            metadata: Must include 'email' for customer email

        Returns:
            Dict with transaction details
        """
        try:
            # Paystack uses kobo for NGN (multiply by 100)
            amount_minor = int(amount * 100)

            # Email is required for Paystack
            email = metadata.get('email') or metadata.get('customer_email')
            if not email:
                raise PaymentGatewayError(
                    message="Customer email is required for Paystack",
                    gateway=self.gateway_name,
                    error_code='missing_email'
                )

            payload = {
                'amount': amount_minor,
                'currency': currency.upper(),
                'email': email,
                'metadata': metadata,
                'callback_url': metadata.get('callback_url', ''),
            }

            # Add channels if specified
            if 'channels' in metadata:
                payload['channels'] = metadata['channels']

            response = requests.post(
                f'{self.BASE_URL}/transaction/initialize',
                json=payload,
                headers=self.headers,
                timeout=30
            )

            result = response.json()

            if not result.get('status'):
                error_msg = result.get('message', 'Transaction initialization failed')
                logger.error(f"Paystack error: {error_msg}")
                raise PaymentGatewayError(
                    message=error_msg,
                    gateway=self.gateway_name,
                    details=result
                )

            data = result['data']
            logger.info(f"Paystack transaction initialized: {data['reference']}")

            return {
                'id': data['reference'],
                'reference': data['reference'],
                'authorization_url': data['authorization_url'],
                'access_code': data['access_code'],
                'status': 'pending',
                'amount': float(amount),
                'currency': currency,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to connect to payment gateway",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in Paystack gateway: {str(e)}")
            raise PaymentGatewayError(
                message="An unexpected error occurred",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def confirm_payment(self, reference: str) -> Dict[str, Any]:
        """
        Verify a Paystack transaction.

        Args:
            reference: The transaction reference

        Returns:
            Dict with payment details and status
        """
        try:
            response = requests.get(
                f'{self.BASE_URL}/transaction/verify/{reference}',
                headers=self.headers,
                timeout=30
            )

            result = response.json()

            if not result.get('status'):
                error_msg = result.get('message', 'Transaction verification failed')
                logger.error(f"Paystack verification error: {error_msg}")
                raise PaymentGatewayError(
                    message=error_msg,
                    gateway=self.gateway_name,
                    error_code='verification_failed',
                    details=result
                )

            data = result['data']

            # Map Paystack status to standard status
            paystack_status = data['status']
            if paystack_status == 'success':
                status = 'succeeded'
            elif paystack_status == 'failed':
                status = 'failed'
            elif paystack_status == 'abandoned':
                status = 'cancelled'
            else:
                status = 'processing'

            # Extract card details if available
            card_details = {}
            if data.get('authorization'):
                auth = data['authorization']
                card_details = {
                    'card_last4': auth.get('last4'),
                    'card_brand': auth.get('brand'),
                    'card_exp_month': auth.get('exp_month'),
                    'card_exp_year': auth.get('exp_year'),
                    'card_type': auth.get('card_type'),
                    'bank': auth.get('bank'),
                }

            return {
                'id': data['reference'],
                'reference': data['reference'],
                'status': status,
                'amount': Decimal(data['amount']) / 100,
                'currency': data['currency'],
                'customer_email': data.get('customer', {}).get('email'),
                'paid_at': data.get('paid_at'),
                'channel': data.get('channel'),
                **card_details,
                'metadata': data.get('metadata', {}),
                'gateway_response': data.get('gateway_response'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to verify payment",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Error confirming Paystack payment: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to confirm payment",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def create_refund(self, transaction_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Create a refund for a Paystack transaction.

        Args:
            transaction_id: The transaction reference or ID
            amount: Refund amount in major currency unit

        Returns:
            Dict with refund details
        """
        try:
            # Paystack uses kobo (multiply by 100)
            amount_minor = int(amount * 100) if amount else None

            payload = {
                'transaction': transaction_id,
            }

            if amount_minor:
                payload['amount'] = amount_minor

            response = requests.post(
                f'{self.BASE_URL}/refund',
                json=payload,
                headers=self.headers,
                timeout=30
            )

            result = response.json()

            if not result.get('status'):
                error_msg = result.get('message', 'Refund creation failed')
                logger.error(f"Paystack refund error: {error_msg}")
                raise PaymentGatewayError(
                    message=error_msg,
                    gateway=self.gateway_name,
                    error_code='refund_failed',
                    details=result
                )

            data = result['data']
            logger.info(f"Paystack refund created: {data.get('id')} for transaction {transaction_id}")

            # Map Paystack refund status
            refund_status = data.get('status', 'pending')
            if refund_status in ['processed', 'success']:
                status = 'succeeded'
            elif refund_status == 'failed':
                status = 'failed'
            else:
                status = 'processing'

            return {
                'id': str(data.get('id')),
                'transaction': data.get('transaction'),
                'status': status,
                'amount': Decimal(data.get('amount', 0)) / 100,
                'currency': data.get('currency'),
                'refunded_by': data.get('refunded_by'),
                'refunded_at': data.get('refunded_at'),
                'customer_note': data.get('customer_note'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to create refund",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Error creating Paystack refund: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to create refund",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str = None) -> bool:
        """
        Verify Paystack webhook signature.

        Args:
            payload: Raw request body
            signature: X-Paystack-Signature header value
            webhook_secret: Webhook secret key

        Returns:
            bool: True if signature is valid
        """
        if not webhook_secret:
            # Use the secret key if webhook secret not provided
            webhook_secret = self.secret_key

        try:
            # Compute HMAC SHA512 hash
            computed_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha512
            ).hexdigest()

            # Compare signatures
            is_valid = hmac.compare_digest(computed_signature, signature)

            if is_valid:
                logger.info("Paystack webhook signature verified")
            else:
                logger.warning("Paystack webhook signature verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Paystack webhook verification error: {str(e)}")
            return False

    def get_supported_currencies(self) -> list:
        """
        Get list of currencies supported by Paystack.

        Returns:
            List of currency codes
        """
        return ['NGN', 'GHS', 'ZAR', 'USD']

    def get_supported_channels(self) -> list:
        """
        Get list of payment channels supported by Paystack.

        Returns:
            List of channel names
        """
        return ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer']

