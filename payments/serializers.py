from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    is_successful = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'order', 'order_number',
            'gateway', 'payment_method', 'amount', 'currency',
            'status', 'transaction_id', 'gateway_response',
            'card_last4', 'card_brand',
            'customer_ip', 'user_agent',
            'error_code', 'error_message', 'retry_count',
            'is_successful',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'uuid', 'transaction_id', 'gateway_response',
            'customer_ip', 'user_agent', 'error_code', 'error_message',
            'retry_count', 'created_at', 'updated_at', 'completed_at'
        ]

    def get_is_successful(self, obj):
        return obj.status == 'succeeded'


class PaymentListSerializer(serializers.ModelSerializer):
    """Minimal payment serializer for lists"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'order_number', 'gateway', 'payment_method',
            'amount', 'currency', 'status', 'created_at'
        ]


class PaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intent"""
    order_id = serializers.IntegerField()
    payment_method = serializers.CharField(max_length=50)
    gateway = serializers.ChoiceField(choices=['stripe', 'paystack', 'paypal'])
    return_url = serializers.URLField(required=False)

    def validate_order_id(self, value):
        from orders.models import Order
        try:
            order = Order.objects.get(id=value)
            if order.payment_status == 'paid':
                raise serializers.ValidationError("This order has already been paid")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")


class PaymentConfirmSerializer(serializers.Serializer):
    """Serializer for confirming payment"""
    payment_intent_id = serializers.CharField()
    gateway = serializers.ChoiceField(choices=['stripe', 'paystack', 'paypal'])


class RefundSerializer(serializers.ModelSerializer):
    """Refund serializer"""
    payment_transaction_id = serializers.CharField(source='payment.transaction_id', read_only=True)
    order_number = serializers.CharField(source='payment.order.order_number', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            'id', 'uuid', 'payment', 'payment_transaction_id', 'order_number',
            'amount', 'reason', 'notes', 'refund_id', 'status',
            'gateway_response', 'created_by', 'created_by_name',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'uuid', 'refund_id', 'status', 'gateway_response',
            'created_by', 'created_at', 'completed_at'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class RefundCreateSerializer(serializers.Serializer):
    """Serializer for creating refunds"""
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.ChoiceField(choices=Refund.REFUND_REASONS)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(id=value)
            if payment.status != 'succeeded':
                raise serializers.ValidationError("Can only refund successful payments")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")

    def validate(self, data):
        payment = Payment.objects.get(id=data['payment_id'])

        # Calculate total refunded amount
        total_refunded = sum(
            refund.amount for refund in payment.refunds.filter(status='succeeded')
        )

        if total_refunded + data['amount'] > payment.amount:
            raise serializers.ValidationError(
                f"Refund amount exceeds available amount. "
                f"Already refunded: {total_refunded}, Payment amount: {payment.amount}"
            )

        return data


class PaymentMethodSerializer(serializers.Serializer):
    """Serializer for payment method details"""
    type = serializers.CharField()
    card_last4 = serializers.CharField(required=False)
    card_brand = serializers.CharField(required=False)
    card_exp_month = serializers.IntegerField(required=False)
    card_exp_year = serializers.IntegerField(required=False)


class PaymentHistorySerializer(serializers.Serializer):
    """Serializer for payment history/timeline"""
    timestamp = serializers.DateTimeField()
    status = serializers.CharField()
    message = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for processing webhook events"""
    event_type = serializers.CharField()
    gateway = serializers.CharField()
    transaction_id = serializers.CharField()
    payload = serializers.JSONField()
    signature = serializers.CharField()

