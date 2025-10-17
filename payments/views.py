"""
Payment Views for Multi-Tenant E-Commerce Platform
"""
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging

from .models import Payment, Refund
from .serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PaymentIntentSerializer,
    PaymentConfirmSerializer,
    RefundSerializer,
    RefundCreateSerializer,
    PaymentHistorySerializer,
    WebhookEventSerializer,
)
from .filters import PaymentFilter, RefundFilter
from api.permissions import CanProcessPayments, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


# ============================================================================
# PAYMENT VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all payments",
        description="Retrieve payment history with filtering",
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, description='Filter by payment status'),
            OpenApiParameter(name='gateway', type=OpenApiTypes.STR, description='Filter by payment gateway'),
            OpenApiParameter(name='order', type=OpenApiTypes.INT, description='Filter by order ID'),
        ],
        tags=['Payments'],
    ),
    retrieve=extend_schema(
        summary="Get payment details",
        description="Retrieve detailed information about a specific payment",
        tags=['Payments'],
    ),
)
class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing payments.

    Handles payment creation, confirmation, and status tracking.
    """
    queryset = Payment.objects.select_related('order').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentFilter
    http_method_names = ['get', 'post']  # No update/delete

    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentListSerializer
        return PaymentSerializer

    def get_queryset(self):
        """Filter payments based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        # Staff can see all payments
        if user.is_staff:
            return queryset

        # Customers can only see their own payments
        return queryset.filter(order__customer=user)

    @extend_schema(
        summary="Create payment intent",
        description="""
        Create a payment intent for an order.

        This initializes the payment process with the selected gateway (Stripe, Paystack, or PayPal).
        Returns payment details including client_secret for frontend payment form.
        """,
        request=PaymentIntentSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Create Stripe Payment',
                value={
                    'order_id': 123,
                    'payment_method': 'card',
                    'gateway': 'stripe',
                    'return_url': 'https://example.com/payment/success'
                },
                request_only=True,
            ),
        ],
        tags=['Payments'],
    )
    @action(detail=False, methods=['post'])
    def create_intent(self, request):
        """Create payment intent"""
        serializer = PaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']
        gateway_name = serializer.validated_data['gateway']
        return_url = serializer.validated_data.get('return_url')

        # Get order
        from orders.models import Order
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

        if order.payment_status == 'paid':
            return Response(
                {'error': 'Order has already been paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get client IP and user agent
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        try:
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                gateway=gateway_name,
                payment_method=payment_method,
                amount=order.total_amount,
                currency=order.currency if hasattr(order, 'currency') else 'USD',
                status='pending',
                customer_ip=client_ip,
                user_agent=user_agent
            )

            # Create payment intent with gateway
            from .gateways import get_gateway
            gateway = get_gateway(gateway_name)

            metadata = {
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_id': request.user.id,
                'customer_email': request.user.email,
                'payment_id': payment.id,
            }

            # Create intent based on gateway
            if gateway_name == 'stripe':
                intent_data = gateway.create_payment_intent(
                    amount=payment.amount,
                    currency=payment.currency,
                    metadata=metadata
                )
                payment.transaction_id = intent_data.get('id')
                payment.gateway_response = intent_data
                payment.save()

                response_data = {
                    'payment_id': payment.id,
                    'client_secret': intent_data.get('client_secret'),
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'status': payment.status
                }

            elif gateway_name == 'paystack':
                metadata['email'] = request.user.email
                intent_data = gateway.create_payment_intent(
                    amount=payment.amount,
                    currency=payment.currency,
                    metadata=metadata
                )
                payment.transaction_id = intent_data.get('reference')
                payment.gateway_response = intent_data
                payment.save()

                response_data = {
                    'payment_id': payment.id,
                    'authorization_url': intent_data.get('authorization_url'),
                    'access_code': intent_data.get('access_code'),
                    'reference': intent_data.get('reference'),
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'status': payment.status
                }

            elif gateway_name == 'paypal':
                metadata['return_url'] = return_url or f"{settings.FRONTEND_URL}/payment/success"
                metadata['cancel_url'] = f"{settings.FRONTEND_URL}/payment/cancel"
                intent_data = gateway.create_payment_intent(
                    amount=payment.amount,
                    currency=payment.currency,
                    metadata=metadata
                )
                payment.transaction_id = intent_data.get('id')
                payment.gateway_response = intent_data
                payment.save()

                response_data = {
                    'payment_id': payment.id,
                    'approval_url': intent_data.get('approval_url'),
                    'order_id': intent_data.get('id'),
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'status': payment.status
                }

            else:
                return Response(
                    {'error': 'Unsupported gateway'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Payment intent created: {payment.id} for order {order.order_number}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Payment intent creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create payment intent', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Confirm payment",
        description="Confirm a payment after user completes payment form",
        request=PaymentConfirmSerializer,
        responses={200: PaymentSerializer},
        tags=['Payments'],
    )
    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """Confirm payment"""
        serializer = PaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_intent_id = serializer.validated_data['payment_intent_id']
        gateway_name = serializer.validated_data['gateway']

        try:
            # Find payment by transaction_id
            payment = Payment.objects.get(
                transaction_id=payment_intent_id,
                gateway=gateway_name
            )

            # Verify with gateway
            from .gateways import get_gateway
            gateway = get_gateway(gateway_name)

            result = gateway.confirm_payment(payment_intent_id)

            # Update payment status
            with transaction.atomic():
                payment.status = result.get('status', 'processing')
                payment.gateway_response = result

                if payment.status == 'succeeded':
                    payment.completed_at = timezone.now()

                    # Update order
                    order = payment.order
                    order.payment_status = 'paid'
                    order.paid_at = timezone.now()
                    order.status = 'processing'
                    order.save()

                    # Extract card details if available
                    if 'card_last4' in result:
                        payment.card_last4 = result['card_last4']
                    if 'card_brand' in result:
                        payment.card_brand = result['card_brand']

                payment.save()

            logger.info(f"Payment confirmed: {payment.id} - Status: {payment.status}")

            serializer = PaymentSerializer(payment)
            return Response(serializer.data)

        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Payment confirmation failed: {str(e)}")
            return Response(
                {'error': 'Payment confirmation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Verify payment",
        description="Verify payment status with gateway",
        tags=['Payments'],
    )
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify payment with gateway"""
        payment = self.get_object()

        if not payment.transaction_id:
            return Response(
                {'error': 'No transaction ID to verify'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from .gateways import get_gateway
            gateway = get_gateway(payment.gateway)

            result = gateway.confirm_payment(payment.transaction_id)

            # Update payment
            old_status = payment.status
            payment.status = result.get('status', payment.status)
            payment.gateway_response = result

            if payment.status == 'succeeded' and old_status != 'succeeded':
                payment.completed_at = timezone.now()

                # Update order
                order = payment.order
                order.payment_status = 'paid'
                order.paid_at = timezone.now()
                order.status = 'processing'
                order.save()

            payment.save()

            serializer = PaymentSerializer(payment)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return Response(
                {'error': 'Verification failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Get payment history",
        description="Get timeline of payment status changes",
        responses={200: PaymentHistorySerializer(many=True)},
        tags=['Payments'],
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get payment history/timeline"""
        payment = self.get_object()

        history = [
            {
                'timestamp': payment.created_at,
                'status': 'pending',
                'message': 'Payment initiated',
                'amount': payment.amount
            }
        ]

        if payment.status in ['processing', 'succeeded', 'failed']:
            history.append({
                'timestamp': payment.updated_at,
                'status': payment.status,
                'message': f'Payment {payment.status}',
                'amount': payment.amount
            })

        if payment.completed_at:
            history.append({
                'timestamp': payment.completed_at,
                'status': 'completed',
                'message': 'Payment completed',
                'amount': payment.amount
            })

        # Add refund history
        for refund in payment.refunds.all():
            history.append({
                'timestamp': refund.created_at,
                'status': 'refunded',
                'message': f'Refund initiated: {refund.reason}',
                'amount': refund.amount
            })

            if refund.completed_at:
                history.append({
                    'timestamp': refund.completed_at,
                    'status': 'refund_completed',
                    'message': 'Refund completed',
                    'amount': refund.amount
                })

        history.sort(key=lambda x: x['timestamp'])

        serializer = PaymentHistorySerializer(history, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Retry failed payment",
        description="Retry a failed payment",
        tags=['Payments'],
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed payment"""
        payment = self.get_object()

        if payment.status not in ['failed', 'cancelled']:
            return Response(
                {'error': 'Can only retry failed or cancelled payments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.retry_count >= 3:
            return Response(
                {'error': 'Maximum retry attempts reached'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset payment status
        payment.status = 'pending'
        payment.retry_count += 1
        payment.error_code = ''
        payment.error_message = ''
        payment.save()

        return Response({
            'message': 'Payment retry initiated',
            'payment_id': payment.id,
            'retry_count': payment.retry_count
        })

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================================
# REFUND VIEWS
# ============================================================================

@extend_schema_view(
    list=extend_schema(
        summary="List all refunds",
        description="Retrieve refund history with filtering",
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, description='Filter by refund status'),
            OpenApiParameter(name='payment', type=OpenApiTypes.INT, description='Filter by payment ID'),
        ],
        tags=['Payments'],
    ),
    retrieve=extend_schema(
        summary="Get refund details",
        description="Retrieve detailed information about a specific refund",
        tags=['Payments'],
    ),
    create=extend_schema(
        summary="Create refund",
        description="Process a refund for a payment. Requires staff permissions.",
        request=RefundCreateSerializer,
        responses={201: RefundSerializer},
        tags=['Payments'],
    ),
)
class RefundViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing refunds.

    Handles refund creation and tracking.
    """
    queryset = Refund.objects.select_related('payment', 'created_by').all()
    serializer_class = RefundSerializer
    permission_classes = [CanProcessPayments]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RefundFilter
    http_method_names = ['get', 'post']  # No update/delete

    def create(self, request, *args, **kwargs):
        """Create refund"""
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_id = serializer.validated_data['payment_id']
        amount = serializer.validated_data['amount']
        reason = serializer.validated_data['reason']
        notes = serializer.validated_data.get('notes', '')

        try:
            payment = Payment.objects.get(id=payment_id)

            # Process refund with gateway
            from .gateways import get_gateway
            gateway = get_gateway(payment.gateway)

            with transaction.atomic():
                # Create refund via gateway
                result = gateway.create_refund(
                    payment_id=payment.transaction_id,
                    amount=amount
                )

                # Create refund record
                refund = Refund.objects.create(
                    payment=payment,
                    amount=amount,
                    reason=reason,
                    notes=notes,
                    refund_id=result.get('id'),
                    status=result.get('status', 'processing'),
                    gateway_response=result,
                    created_by=request.user
                )

                # Update payment status if fully refunded
                total_refunded = sum(
                    r.amount for r in payment.refunds.filter(status='succeeded')
                ) + amount

                if total_refunded >= payment.amount:
                    payment.status = 'refunded'
                    payment.save()

                    # Update order
                    order = payment.order
                    order.payment_status = 'refunded'
                    order.status = 'refunded'
                    order.save()

            logger.info(f"Refund created: {refund.id} for payment {payment.id}")

            refund_serializer = RefundSerializer(refund)
            return Response(refund_serializer.data, status=status.HTTP_201_CREATED)

        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Refund creation failed: {str(e)}")
            return Response(
                {'error': 'Refund failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Check refund status",
        description="Check refund status with gateway",
        tags=['Payments'],
    )
    @action(detail=True, methods=['post'])
    def check_status(self, request, pk=None):
        """Check refund status with gateway"""
        refund = self.get_object()

        try:
            from .gateways import get_gateway
            gateway = get_gateway(refund.payment.gateway)

            # Verify refund status
            # Implementation depends on gateway capabilities

            refund.save()

            serializer = self.get_serializer(refund)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Refund status check failed: {str(e)}")
            return Response(
                {'error': 'Status check failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# WEBHOOK VIEWS
# ============================================================================

@extend_schema(
    summary="Handle payment webhooks",
    description="""
    Webhook endpoint for payment gateway callbacks.

    Handles events from Stripe, Paystack, and PayPal.
    """,
    request=WebhookEventSerializer,
    responses={200: OpenApiTypes.OBJECT},
    tags=['Payments'],
)
class PaymentWebhookView(views.APIView):
    """
    Webhook endpoint for payment gateways.

    Processes payment status updates from external gateways.
    """
    permission_classes = [AllowAny]  # Webhooks don't use standard auth

    def post(self, request, gateway):
        """Handle webhook event"""
        try:
            # Get gateway
            from .gateways import get_gateway
            gateway_obj = get_gateway(gateway)

            # Verify webhook signature
            signature = request.META.get('HTTP_STRIPE_SIGNATURE') or \
                       request.META.get('HTTP_X_PAYSTACK_SIGNATURE') or \
                       request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG')

            if not signature:
                return Response(
                    {'error': 'Missing signature'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify webhook
            webhook_secret = getattr(settings, f'{gateway.upper()}_WEBHOOK_SECRET', '')
            is_valid = gateway_obj.verify_webhook(
                payload=request.body,
                signature=signature,
                webhook_secret=webhook_secret
            )

            if not is_valid:
                logger.warning(f"Invalid webhook signature from {gateway}")
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Process event
            event_data = request.data
            event_type = event_data.get('type') or event_data.get('event')

            logger.info(f"Processing webhook: {gateway} - {event_type}")

            # Handle payment events
            if 'payment' in event_type or 'charge' in event_type:
                self._handle_payment_event(gateway, event_data)

            # Handle refund events
            elif 'refund' in event_type:
                self._handle_refund_event(gateway, event_data)

            return Response({'status': 'success'})

        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return Response(
                {'error': 'Webhook processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_payment_event(self, gateway, event_data):
        """Handle payment-related webhook events"""
        try:
            # Extract transaction ID (varies by gateway)
            if gateway == 'stripe':
                transaction_id = event_data.get('data', {}).get('object', {}).get('id')
            elif gateway == 'paystack':
                transaction_id = event_data.get('data', {}).get('reference')
            elif gateway == 'paypal':
                transaction_id = event_data.get('resource', {}).get('id')
            else:
                return

            if not transaction_id:
                return

            # Find and update payment
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)

                # Update status based on event
                event_type = event_data.get('type') or event_data.get('event')

                if 'succeeded' in event_type or 'completed' in event_type:
                    payment.status = 'succeeded'
                    payment.completed_at = timezone.now()

                    # Update order
                    order = payment.order
                    order.payment_status = 'paid'
                    order.paid_at = timezone.now()
                    order.status = 'processing'
                    order.save()

                elif 'failed' in event_type:
                    payment.status = 'failed'
                    payment.error_message = event_data.get('data', {}).get('message', 'Payment failed')

                payment.gateway_response = event_data
                payment.save()

                logger.info(f"Payment updated via webhook: {payment.id} - {payment.status}")

            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for transaction: {transaction_id}")

        except Exception as e:
            logger.error(f"Payment event handling failed: {str(e)}")

    def _handle_refund_event(self, gateway, event_data):
        """Handle refund-related webhook events"""
        try:
            # Extract refund ID
            if gateway == 'stripe':
                refund_id = event_data.get('data', {}).get('object', {}).get('id')
            elif gateway == 'paystack':
                refund_id = event_data.get('data', {}).get('id')
            else:
                return

            if not refund_id:
                return

            # Find and update refund
            try:
                refund = Refund.objects.get(refund_id=refund_id)

                # Update status
                event_type = event_data.get('type') or event_data.get('event')

                if 'succeeded' in event_type:
                    refund.status = 'succeeded'
                    refund.completed_at = timezone.now()
                elif 'failed' in event_type:
                    refund.status = 'failed'

                refund.gateway_response = event_data
                refund.save()

                logger.info(f"Refund updated via webhook: {refund.id} - {refund.status}")

            except Refund.DoesNotExist:
                logger.warning(f"Refund not found: {refund_id}")

        except Exception as e:
            logger.error(f"Refund event handling failed: {str(e)}")
