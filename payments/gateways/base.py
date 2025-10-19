"""
Base Payment Gateway Abstract Class

This module defines the abstract base class that all payment gateway
implementations must inherit from.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from decimal import Decimal


class PaymentGateway(ABC):
    """
    Abstract base class for payment gateway implementations.

    All payment gateways (Stripe, Paystack, PayPal) must implement
    these methods to ensure consistent interface.
    """

    def __init__(self, api_key: str = None, **kwargs):
        """
        Initialize the payment gateway.

        Args:
            api_key: API key/secret for the gateway
            **kwargs: Additional configuration parameters
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    def create_payment_intent(self, amount: Decimal, currency: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment intent/transaction.

        Args:
            amount: Payment amount
            currency: Currency code (USD, NGN, etc.)
            metadata: Additional metadata (order_id, customer_email, etc.)

        Returns:
            Dict containing:
                - id: Payment intent/transaction ID
                - client_secret or authorization_url: For client-side payment
                - status: Current payment status
                - additional gateway-specific fields

        Raises:
            PaymentGatewayError: If payment intent creation fails
        """
        pass

    @abstractmethod
    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Confirm/verify a payment.

        Args:
            payment_intent_id: The payment intent/transaction ID

        Returns:
            Dict containing:
                - id: Payment ID
                - status: Payment status (succeeded, failed, etc.)
                - amount: Payment amount
                - currency: Currency code
                - additional gateway-specific fields

        Raises:
            PaymentGatewayError: If payment confirmation fails
        """
        pass

    @abstractmethod
    def create_refund(self, payment_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Create a refund for a payment.

        Args:
            payment_id: The original payment ID
            amount: Refund amount

        Returns:
            Dict containing:
                - id: Refund ID
                - status: Refund status
                - amount: Refund amount
                - additional gateway-specific fields

        Raises:
            PaymentGatewayError: If refund creation fails
        """
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str, webhook_secret: str = None) -> bool:
        """
        Verify webhook signature for security.

        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers
            webhook_secret: Webhook secret for verification

        Returns:
            bool: True if signature is valid, False otherwise
        """
        pass

    def get_payment_status(self, payment_id: str) -> str:
        """
        Get the current status of a payment.

        This is a convenience method that calls confirm_payment
        and extracts just the status.

        Args:
            payment_id: The payment ID

        Returns:
            str: Payment status
        """
        result = self.confirm_payment(payment_id)
        return result.get('status', 'unknown')


class PaymentGatewayError(Exception):
    """
    Custom exception for payment gateway errors.
    """

    def __init__(self, message: str, gateway: str = None, error_code: str = None, details: Dict = None):
        """
        Initialize payment gateway error.

        Args:
            message: Error message
            gateway: Gateway name (stripe, paystack, paypal)
            error_code: Gateway-specific error code
            details: Additional error details
        """
        self.message = message
        self.gateway = gateway
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        error_str = f"PaymentGatewayError: {self.message}"
        if self.gateway:
            error_str += f" (Gateway: {self.gateway})"
        if self.error_code:
            error_str += f" [Code: {self.error_code}]"
        return error_str

