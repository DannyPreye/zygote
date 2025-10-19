"""
PayPal Payment Gateway Implementation
"""
from decimal import Decimal
from typing import Dict, Any
import logging
import requests
import base64

from .base import PaymentGateway, PaymentGatewayError

logger = logging.getLogger(__name__)


class PayPalGateway(PaymentGateway):
    """
    PayPal payment gateway implementation.

    Handles payment processing through PayPal REST API.
    Documentation: https://developer.paypal.com/docs/api/overview/
    """

    SANDBOX_URL = "https://api-m.sandbox.paypal.com"
    LIVE_URL = "https://api-m.paypal.com"

    def __init__(self, client_id: str, client_secret: str, mode: str = 'sandbox', **kwargs):
        """
        Initialize PayPal gateway.

        Args:
            client_id: PayPal client ID
            client_secret: PayPal client secret
            mode: 'sandbox' or 'live'
            **kwargs: Additional configuration
        """
        super().__init__(api_key=client_id, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = mode
        self.base_url = self.SANDBOX_URL if mode == 'sandbox' else self.LIVE_URL
        self.gateway_name = 'paypal'
        self.access_token = None

    def _get_access_token(self) -> str:
        """
        Get OAuth access token from PayPal.

        Returns:
            str: Access token
        """
        try:
            # Create basic auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(
                f'{self.base_url}/v1/oauth2/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                timeout=30
            )

            if response.status_code != 200:
                raise PaymentGatewayError(
                    message="Failed to authenticate with PayPal",
                    gateway=self.gateway_name,
                    error_code='auth_failed'
                )

            result = response.json()
            self.access_token = result['access_token']
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal authentication error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to connect to PayPal",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with access token."""
        if not self.access_token:
            self._get_access_token()

        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }

    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a PayPal order.

        Args:
            amount: Payment amount in major currency unit
            currency: Currency code (USD, EUR, GBP, etc.)
            metadata: Must include return_url and cancel_url

        Returns:
            Dict with order details
        """
        try:
            # Build order payload
            payload = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': currency.upper(),
                        'value': str(amount)
                    },
                    'description': f"Order #{metadata.get('order_number', 'N/A')}",
                    'custom_id': str(metadata.get('order_id', '')),
                    'invoice_id': str(metadata.get('order_number', '')),
                }],
                'application_context': {
                    'return_url': metadata.get('return_url', ''),
                    'cancel_url': metadata.get('cancel_url', ''),
                    'brand_name': metadata.get('brand_name', 'Your Store'),
                    'shipping_preference': 'NO_SHIPPING',
                    'user_action': 'PAY_NOW'
                }
            }

            response = requests.post(
                f'{self.base_url}/v2/checkout/orders',
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code not in [200, 201]:
                error_data = response.json()
                error_msg = error_data.get('message', 'Order creation failed')
                logger.error(f"PayPal error: {error_msg}")
                raise PaymentGatewayError(
                    message=error_msg,
                    gateway=self.gateway_name,
                    details=error_data
                )

            result = response.json()
            logger.info(f"PayPal order created: {result['id']}")

            # Extract approval URL
            approval_url = ''
            for link in result.get('links', []):
                if link['rel'] == 'approve':
                    approval_url = link['href']
                    break

            return {
                'id': result['id'],
                'approval_url': approval_url,
                'status': result['status'].lower(),
                'amount': float(amount),
                'currency': currency,
                'created': result.get('create_time'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to connect to payment gateway",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Unexpected error in PayPal gateway: {str(e)}")
            raise PaymentGatewayError(
                message="An unexpected error occurred",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def confirm_payment(self, order_id: str) -> Dict[str, Any]:
        """
        Capture/verify a PayPal order.

        Args:
            order_id: The PayPal order ID

        Returns:
            Dict with payment details and status
        """
        try:
            # First, get order details
            response = requests.get(
                f'{self.base_url}/v2/checkout/orders/{order_id}',
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"PayPal order not found: {order_id}")
                raise PaymentGatewayError(
                    message="Order not found",
                    gateway=self.gateway_name,
                    error_code='not_found',
                    details=error_data
                )

            result = response.json()

            # If order is approved but not captured, capture it
            if result['status'] == 'APPROVED':
                capture_response = requests.post(
                    f'{self.base_url}/v2/checkout/orders/{order_id}/capture',
                    headers=self._get_headers(),
                    timeout=30
                )

                if capture_response.status_code in [200, 201]:
                    result = capture_response.json()

            # Map PayPal status to standard status
            paypal_status = result['status']
            if paypal_status == 'COMPLETED':
                status = 'succeeded'
            elif paypal_status in ['APPROVED', 'CREATED']:
                status = 'processing'
            elif paypal_status in ['VOIDED', 'CANCELLED']:
                status = 'cancelled'
            else:
                status = 'failed'

            # Extract amount
            amount = Decimal('0')
            if result.get('purchase_units'):
                amount = Decimal(result['purchase_units'][0]['amount']['value'])

            # Extract payer details
            payer_details = {}
            if result.get('payer'):
                payer = result['payer']
                payer_details = {
                    'payer_id': payer.get('payer_id'),
                    'email': payer.get('email_address'),
                    'name': payer.get('name', {}).get('given_name', '') + ' ' +
                            payer.get('name', {}).get('surname', ''),
                }

            return {
                'id': result['id'],
                'status': status,
                'amount': amount,
                'currency': result['purchase_units'][0]['amount']['currency_code'] if result.get('purchase_units') else '',
                'created': result.get('create_time'),
                'updated': result.get('update_time'),
                **payer_details,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to verify payment",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Error confirming PayPal payment: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to confirm payment",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def create_refund(self, capture_id: str, amount: Decimal = None) -> Dict[str, Any]:
        """
        Create a refund for a PayPal capture.

        Args:
            capture_id: The capture ID (not order ID)
            amount: Refund amount (None for full refund)

        Returns:
            Dict with refund details
        """
        try:
            payload = {}
            if amount:
                payload['amount'] = {
                    'value': str(amount),
                    'currency_code': 'USD'  # Should be passed as parameter
                }

            response = requests.post(
                f'{self.base_url}/v2/payments/captures/{capture_id}/refund',
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code not in [200, 201]:
                error_data = response.json()
                error_msg = error_data.get('message', 'Refund creation failed')
                logger.error(f"PayPal refund error: {error_msg}")
                raise PaymentGatewayError(
                    message=error_msg,
                    gateway=self.gateway_name,
                    error_code='refund_failed',
                    details=error_data
                )

            result = response.json()
            logger.info(f"PayPal refund created: {result['id']} for capture {capture_id}")

            # Map PayPal refund status
            refund_status = result['status']
            if refund_status == 'COMPLETED':
                status = 'succeeded'
            elif refund_status == 'PENDING':
                status = 'processing'
            else:
                status = 'failed'

            refund_amount = Decimal('0')
            if result.get('amount'):
                refund_amount = Decimal(result['amount']['value'])

            return {
                'id': result['id'],
                'status': status,
                'amount': refund_amount,
                'currency': result.get('amount', {}).get('currency_code', ''),
                'capture_id': capture_id,
                'created': result.get('create_time'),
                'updated': result.get('update_time'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal connection error: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to create refund",
                gateway=self.gateway_name,
                error_code='connection_error',
                details={'error': str(e)}
            )

        except PaymentGatewayError:
            raise

        except Exception as e:
            logger.error(f"Error creating PayPal refund: {str(e)}")
            raise PaymentGatewayError(
                message="Failed to create refund",
                gateway=self.gateway_name,
                details={'error': str(e)}
            )

    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str = None) -> bool:
        """
        Verify PayPal webhook signature.

        Note: PayPal webhook verification is more complex and requires
        additional parameters. This is a simplified version.

        Args:
            payload: Raw request body
            signature: Webhook signature header
            webhook_secret: Webhook ID

        Returns:
            bool: True if signature is valid
        """
        # PayPal webhook verification requires calling their verification API
        # This is a simplified implementation
        logger.warning("PayPal webhook verification not fully implemented")
        return True  # TODO: Implement proper verification

    def get_supported_currencies(self) -> list:
        """
        Get list of major currencies supported by PayPal.

        Returns:
            List of currency codes
        """
        return [
            'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF',
            'CNY', 'SEK', 'NZD', 'MXN', 'SGD', 'HKD', 'NOK',
            'KRW', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR'
        ]

