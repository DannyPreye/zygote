"""
Custom Authentication Backend with Enhanced Security
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SecureAuthenticationBackend(ModelBackend):
    """
    Enhanced authentication backend with:
    - Account lockout after failed attempts
    - Login attempt tracking
    - Suspicious activity detection
    """

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 30  # minutes

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate with security checks"""
        if username is None:
            username = kwargs.get('email')

        if not username or not password:
            return None

        # Check if account is locked
        if self.is_account_locked(username):
            logger.warning(f"Login attempt on locked account: {username}")
            return None

        try:
            # Try to find user by username or email
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                # Increment failed attempts even for non-existent users to prevent enumeration
                self.increment_failed_attempts(username)
                return None

        # Check password
        if user.check_password(password):
            # Verify account is active
            if not user.is_active:
                logger.warning(f"Inactive user login attempt: {username}")
                return None

            # Reset failed attempts on successful login
            self.reset_failed_attempts(username)

            # Log successful login
            self.log_login_attempt(user, request, success=True)

            return user
        else:
            # Increment failed attempts
            self.increment_failed_attempts(username)
            self.log_login_attempt(user, request, success=False)

            # Check if account should be locked
            attempts = self.get_failed_attempts(username)
            if attempts >= self.MAX_FAILED_ATTEMPTS:
                self.lock_account(username)
                logger.warning(f"Account locked due to failed attempts: {username}")

            return None

    def is_account_locked(self, username):
        """Check if account is currently locked"""
        lock_key = f"account_locked:{username}"
        return cache.get(lock_key, False)

    def lock_account(self, username):
        """Lock account for specified duration"""
        lock_key = f"account_locked:{username}"
        cache.set(lock_key, True, self.LOCKOUT_DURATION * 60)

    def get_failed_attempts(self, username):
        """Get number of failed login attempts"""
        attempts_key = f"failed_attempts:{username}"
        return cache.get(attempts_key, 0)

    def increment_failed_attempts(self, username):
        """Increment failed login attempts counter"""
        attempts_key = f"failed_attempts:{username}"
        attempts = cache.get(attempts_key, 0)
        cache.set(attempts_key, attempts + 1, self.LOCKOUT_DURATION * 60)

    def reset_failed_attempts(self, username):
        """Reset failed login attempts"""
        attempts_key = f"failed_attempts:{username}"
        cache.delete(attempts_key)

    def log_login_attempt(self, user, request, success=True):
        """Log login attempt for security auditing"""
        from .models import LoginAttempt

        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        LoginAttempt.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            timestamp=timezone.now()
        )

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class EmailAuthenticationBackend(SecureAuthenticationBackend):
    """Allow authentication using email address"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email', username)
        return super().authenticate(request, username=email, password=password, **kwargs)

