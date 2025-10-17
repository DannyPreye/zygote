"""
Custom Throttling Classes for API Rate Limiting
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle
from django.core.cache import cache


class BurstRateThrottle(UserRateThrottle):
    """
    High-frequency rate limiting for burst protection
    """
    scope = 'burst'
    rate = '60/minute'


class SustainedRateThrottle(UserRateThrottle):
    """
    Sustained rate limiting for overall API usage
    """
    scope = 'sustained'
    rate = '1000/day'


class LoginRateThrottle(AnonRateThrottle):
    """
    Strict rate limiting for login attempts
    """
    scope = 'login'
    rate = '5/minute'


class RegisterRateThrottle(AnonRateThrottle):
    """
    Rate limiting for registration
    """
    scope = 'register'
    rate = '3/hour'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate limiting for password reset requests
    """
    scope = 'password_reset'
    rate = '3/hour'


class PaymentRateThrottle(UserRateThrottle):
    """
    Conservative rate limiting for payment operations
    """
    scope = 'payment'
    rate = '10/hour'


class SearchRateThrottle(SimpleRateThrottle):
    """
    Rate limiting for search operations
    """
    scope = 'search'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def allow_request(self, request, view):
        """
        Implement per-IP rate limiting for anonymous users
        """
        if request.user.is_authenticated:
            self.rate = '100/hour'
        else:
            self.rate = '20/hour'

        return super().allow_request(request, view)


class CheckoutRateThrottle(UserRateThrottle):
    """
    Rate limiting for checkout operations to prevent fraud
    """
    scope = 'checkout'
    rate = '10/hour'


class EmailRateThrottle(UserRateThrottle):
    """
    Rate limiting for email-related operations
    """
    scope = 'email'
    rate = '5/hour'


class VIPRateThrottle(UserRateThrottle):
    """
    Relaxed rate limiting for VIP customers
    """
    scope = 'vip'

    def allow_request(self, request, view):
        if request.user.is_authenticated and request.user.is_vip:
            self.rate = '10000/day'  # Much higher limit for VIP
        else:
            self.rate = '1000/day'

        return super().allow_request(request, view)


class TenantRateThrottle(SimpleRateThrottle):
    """
    Per-tenant rate limiting
    """
    scope = 'tenant'

    def get_cache_key(self, request, view):
        if hasattr(request, 'tenant'):
            ident = request.tenant.schema_name
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def allow_request(self, request, view):
        # Different rates based on tenant subscription
        if hasattr(request, 'tenant'):
            # Get tenant's subscription plan
            tenant = request.tenant
            if tenant.subscription_plan == 'enterprise':
                self.rate = '100000/day'
            elif tenant.subscription_plan == 'professional':
                self.rate = '50000/day'
            elif tenant.subscription_plan == 'basic':
                self.rate = '10000/day'
            else:  # trial
                self.rate = '1000/day'
        else:
            self.rate = '1000/day'

        return super().allow_request(request, view)


class DynamicRateThrottle(UserRateThrottle):
    """
    Dynamic rate limiting based on user reputation/behavior
    """
    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            self.rate = '100/hour'
            return super().allow_request(request, view)

        # Check user's reputation/violation history
        violation_key = f'throttle_violations:{request.user.id}'
        violations = cache.get(violation_key, 0)

        if violations > 10:
            # Severely restrict abusive users
            self.rate = '10/hour'
        elif violations > 5:
            # Moderately restrict suspicious users
            self.rate = '100/hour'
        elif request.user.is_vip:
            # Generous limits for VIP
            self.rate = '10000/hour'
        else:
            # Standard rate for good standing users
            self.rate = '1000/hour'

        allowed = super().allow_request(request, view)

        if not allowed:
            # Track violations
            cache.set(violation_key, violations + 1, 86400)  # 24 hours

        return allowed


class IPBasedThrottle(SimpleRateThrottle):
    """
    IP-based rate limiting to prevent abuse from single IPs
    """
    scope = 'ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

    def allow_request(self, request, view):
        self.rate = '1000/hour'
        return super().allow_request(request, view)


class AdminRateThrottle(UserRateThrottle):
    """
    Very high rate limit for admin users
    """
    scope = 'admin'

    def allow_request(self, request, view):
        if request.user.is_staff or request.user.is_superuser:
            return True  # No throttling for admins

        self.rate = '1000/hour'
        return super().allow_request(request, view)

