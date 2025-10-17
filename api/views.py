"""
Authentication Views with Enhanced Security
"""
from rest_framework import status, generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.contrib.auth import get_user_model, logout
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .serializers import *
from .models import *
from .authentication import SecureAuthenticationBackend
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """Throttle for login attempts"""
    rate = '5/minute'


class PasswordResetRateThrottle(AnonRateThrottle):
    """Throttle for password reset requests"""
    rate = '3/hour'


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with enhanced security"""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            # Log failed attempt
            username = request.data.get('username') or request.data.get('email')
            ip_address = SecureAuthenticationBackend.get_client_ip(request)

            LoginAttempt.objects.create(
                username=username,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False,
                failure_reason=str(e.detail)
            )

            raise

        user = serializer.validated_data['user']

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Track token
        RefreshTokenHistory.objects.create(
            user=user,
            jti=str(refresh['jti']),
            token=str(refresh),
            expires_at=timezone.now() + timedelta(days=7),
            ip_address=SecureAuthenticationBackend.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Create session activity
        if hasattr(request, 'session'):
            SessionActivity.objects.create(
                user=user,
                session_key=request.session.session_key,
                ip_address=SecureAuthenticationBackend.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        # Log security event
        SecurityLog.objects.create(
            user=user,
            event_type='login',
            description=f'User logged in from {SecureAuthenticationBackend.get_client_ip(request)}',
            ip_address=SecureAuthenticationBackend.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name(),
                'is_verified': user.is_verified,
                'is_vip': user.is_vip,
            }
        }, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email
        self.send_verification_email(user, request)

        # Log security event
        SecurityLog.objects.create(
            user=user,
            event_type='login',
            description='New user registered',
            ip_address=SecureAuthenticationBackend.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'message': 'Registration successful. Please check your email to verify your account.',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

    def send_verification_email(self, user, request):
        """Send email verification link"""
        # Create verification token
        token = EmailVerificationToken.objects.create(
            user=user,
            email=user.email,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Build verification URL
        verification_url = f"{request.scheme}://{request.get_host()}/api/auth/verify-email/{token.token}/"

        # Send email
        subject = 'Verify Your Email Address'
        message = f"""
        Hello {user.first_name},

        Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create an account, please ignore this email.

        Best regards,
        Multi-Tenant Store Team
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")


class EmailVerificationView(views.APIView):
    """Verify email address"""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = EmailVerificationToken.objects.get(
                token=serializer.validated_data['token']
            )

            if not token_obj.is_valid():
                return Response(
                    {'error': 'Token has expired or already been used'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token_obj.mark_as_verified()

            return Response({
                'message': 'Email verified successfully'
            }, status=status.HTTP_200_OK)

        except EmailVerificationToken.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(views.APIView):
    """Request password reset"""
    permission_classes = (AllowAny,)
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            # Create reset token
            token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
                ip_address=SecureAuthenticationBackend.get_client_ip(request)
            )

            # Send reset email
            reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{token.token}/"

            subject = 'Password Reset Request'
            message = f"""
            Hello {user.first_name},

            You requested to reset your password. Click the link below to proceed:

            {reset_url}

            This link will expire in 1 hour.

            If you didn't request this, please ignore this email and ensure your account is secure.

            Best regards,
            Multi-Tenant Store Team
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Log security event
            SecurityLog.objects.create(
                user=user,
                event_type='password_reset',
                description='Password reset requested',
                ip_address=SecureAuthenticationBackend.get_client_ip(request)
            )

        except User.DoesNotExist:
            # Don't reveal if email exists
            pass

        return Response({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(views.APIView):
    """Confirm password reset"""
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = PasswordResetToken.objects.get(
                token=serializer.validated_data['token']
            )

            if not token_obj.is_valid():
                return Response(
                    {'error': 'Token has expired or already been used'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reset password
            user = token_obj.user
            user.set_password(serializer.validated_data['password'])
            user.save()

            # Mark token as used
            token_obj.mark_as_used()

            # Revoke all refresh tokens
            RefreshTokenHistory.objects.filter(user=user, revoked=False).update(
                revoked=True,
                revoked_at=timezone.now()
            )

            # Log security event
            SecurityLog.objects.create(
                user=user,
                event_type='password_reset',
                description='Password was reset',
                ip_address=SecureAuthenticationBackend.get_client_ip(request)
            )

            return Response({
                'message': 'Password reset successfully'
            }, status=status.HTTP_200_OK)

        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(views.APIView):
    """Change password for authenticated user"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Revoke all refresh tokens
        RefreshTokenHistory.objects.filter(user=user, revoked=False).update(
            revoked=True,
            revoked_at=timezone.now()
        )

        # Log security event
        SecurityLog.objects.create(
            user=user,
            event_type='password_change',
            description='Password changed',
            ip_address=SecureAuthenticationBackend.get_client_ip(request)
        )

        return Response({
            'message': 'Password changed successfully. Please login again.'
        }, status=status.HTTP_200_OK)


class TwoFactorSetupView(views.APIView):
    """Setup two-factor authentication"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = TwoFactorSetupSerializer(data={}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(result, status=status.HTTP_200_OK)


class TwoFactorVerifyView(views.APIView):
    """Verify and enable two-factor authentication"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='2fa_enabled',
            description='Two-factor authentication enabled',
            ip_address=SecureAuthenticationBackend.get_client_ip(request)
        )

        return Response({
            'message': 'Two-factor authentication enabled successfully'
        }, status=status.HTTP_200_OK)


class TwoFactorDisableView(views.APIView):
    """Disable two-factor authentication"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = TwoFactorDisableSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        if hasattr(user, 'two_factor'):
            user.two_factor.is_enabled = False
            user.two_factor.save()

            # Log security event
            SecurityLog.objects.create(
                user=user,
                event_type='2fa_disabled',
                description='Two-factor authentication disabled',
                ip_address=SecureAuthenticationBackend.get_client_ip(request)
            )

        return Response({
            'message': 'Two-factor authentication disabled'
        }, status=status.HTTP_200_OK)


class LogoutView(views.APIView):
    """Logout user and revoke tokens"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        if serializer.validated_data.get('all_devices'):
            # Revoke all refresh tokens
            RefreshTokenHistory.objects.filter(user=user, revoked=False).update(
                revoked=True,
                revoked_at=timezone.now()
            )

            # Deactivate all sessions
            SessionActivity.objects.filter(user=user, is_active=True).update(
                is_active=False
            )
        else:
            # Revoke only current refresh token if provided
            refresh_token = serializer.validated_data.get('refresh_token')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    RefreshTokenHistory.objects.filter(jti=str(token['jti'])).update(
                        revoked=True,
                        revoked_at=timezone.now()
                    )
                except Exception:
                    pass

            # Deactivate current session
            if hasattr(request, 'session'):
                SessionActivity.objects.filter(
                    user=user,
                    session_key=request.session.session_key
                ).update(is_active=False)

        # Django logout
        logout(request)

        # Log security event
        SecurityLog.objects.create(
            user=user,
            event_type='logout',
            description='User logged out',
            ip_address=SecureAuthenticationBackend.get_client_ip(request)
        )

        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)


class ActiveSessionsView(generics.ListAPIView):
    """List user's active sessions"""
    permission_classes = (IsAuthenticated,)
    serializer_class = SessionActivitySerializer

    def get_queryset(self):
        return SessionActivity.objects.filter(
            user=self.request.user,
            is_active=True
        )


class RevokeSessionView(views.APIView):
    """Revoke a specific session"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, session_id):
        try:
            session = SessionActivity.objects.get(
                id=session_id,
                user=request.user
            )
            session.is_active = False
            session.save()

            return Response({
                'message': 'Session revoked successfully'
            }, status=status.HTTP_200_OK)
        except SessionActivity.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class LoginHistoryView(generics.ListAPIView):
    """View login attempt history"""
    permission_classes = (IsAuthenticated,)
    serializer_class = LoginAttemptSerializer

    def get_queryset(self):
        return LoginAttempt.objects.filter(user=self.request.user)[:50]


class SecurityActivityView(views.APIView):
    """View security activity log"""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        logs = SecurityLog.objects.filter(user=request.user)[:50]

        return Response({
            'recent_activity': [
                {
                    'event_type': log.event_type,
                    'description': log.description,
                    'ip_address': log.ip_address,
                    'timestamp': log.timestamp
                }
                for log in logs
            ]
        }, status=status.HTTP_200_OK)

