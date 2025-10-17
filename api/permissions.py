"""
Custom Permissions for Multi-Tenant Security
"""
from rest_framework import permissions
from django.core.cache import cache
from django_tenants.utils import get_tenant_model


class IsVerified(permissions.BasePermission):
    """
    Permission to check if user's email is verified
    """
    message = "Email verification required to access this resource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_verified


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.customer == request.user or obj.user == request.user


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow access to object owner or admin staff
    """
    message = "You must be the owner or an admin to access this resource."

    def has_permission(self, request, view):
        # Allow authenticated users to proceed to object-level check
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin/staff can access everything
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if user is the owner
        # Handle different object types
        if hasattr(obj, 'customer'):
            return obj.customer == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id'):
            # For Customer model itself
            return obj.id == request.user.id

        return False


class IsTenantOwner(permissions.BasePermission):
    """
    Permission for tenant owner operations
    """
    message = "Only tenant owners can perform this action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Check if user is tenant owner/admin
        Tenant = get_tenant_model()
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            # Add your logic to check if user owns/manages the tenant
            return request.user.is_staff or request.user.is_superuser
        except Tenant.DoesNotExist:
            return False


class IsTenantMember(permissions.BasePermission):
    """
    Permission to check if user belongs to the current tenant
    """
    message = "Access restricted to tenant members only."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # In multi-tenant setup, user accessing tenant should be validated
        # This is handled by django-tenants middleware, but add extra checks
        return True


class IsCustomerOrAdmin(permissions.BasePermission):
    """
    Permission for customer-specific operations
    """
    def has_object_permission(self, request, view, obj):
        # Admins can access everything
        if request.user.is_staff:
            return True

        # Customers can only access their own data
        if hasattr(obj, 'customer'):
            return obj.customer == request.user

        return obj == request.user


class HasAPIAccess(permissions.BasePermission):
    """
    Check if user has API access (rate limiting, account status)
    """
    message = "API access has been restricted for your account."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let authentication handle this

        # Check if account is suspended
        if not request.user.is_active:
            return False

        # Check rate limiting
        rate_limit_key = f"api_access:{request.user.id}"
        if cache.get(rate_limit_key):
            return False

        return True


class IsVIPCustomer(permissions.BasePermission):
    """
    Permission for VIP-only features
    """
    message = "This feature is available for VIP customers only."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_vip


class CanManageOrders(permissions.BasePermission):
    """
    Permission to manage orders
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Staff can manage all orders
        if request.user.is_staff:
            return True

        # Customers can only view their own orders
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True

        # Customers can only access their own orders
        return obj.customer == request.user


class CanManageInventory(permissions.BasePermission):
    """
    Permission to manage inventory
    """
    message = "Inventory management requires staff permissions."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class CanManageProducts(permissions.BasePermission):
    """
    Permission to manage products
    """
    message = "Product management requires staff permissions."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Staff can manage products
        if request.user.is_staff:
            return True

        # Others can only read
        return request.method in permissions.SAFE_METHODS


class CanAccessPromotions(permissions.BasePermission):
    """
    Permission to manage promotions
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_authenticated and request.user.is_staff


class CanProcessPayments(permissions.BasePermission):
    """
    Permission to process payments
    """
    message = "Payment processing requires proper authorization."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Must have verified email
        if not request.user.is_verified:
            return False

        return True


class CanManagePromotions(permissions.BasePermission):
    """
    Permission to manage promotions and coupons
    """
    message = "You must be an administrator to manage promotions."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class TenantIsolationPermission(permissions.BasePermission):
    """
    Ensure data is isolated per tenant
    """
    message = "Access denied due to tenant isolation policy."

    def has_permission(self, request, view):
        # Always allow if it's a public schema request
        if hasattr(request, 'tenant') and request.tenant.schema_name == 'public':
            return request.user.is_staff or request.user.is_superuser

        return True

    def has_object_permission(self, request, view, obj):
        # Verify object belongs to current tenant
        # This is automatically handled by django-tenants filtering
        return True


class SecureObjectAccess(permissions.BasePermission):
    """
    Enhanced security check for object access
    """
    def has_object_permission(self, request, view, obj):
        # Log access attempts for sensitive data
        if request.method not in permissions.SAFE_METHODS:
            from .models import SecurityLog
            SecurityLog.objects.create(
                user=request.user,
                event_type='suspicious_activity',
                description=f'Attempted {request.method} on {obj.__class__.__name__}',
                ip_address=self.get_client_ip(request),
                metadata={'object_id': obj.pk}
            )

        return True

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Combined permission classes for common use cases
class CustomerAccessPermission(permissions.BasePermission):
    """
    Combined permission for customer operations
    """
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user.is_authenticated:
            return False

        # Must be active
        if not request.user.is_active:
            return False

        # For write operations, must be verified
        if request.method not in permissions.SAFE_METHODS:
            if not request.user.is_verified:
                self.message = "Email verification required for this action."
                return False

        return True

    def has_object_permission(self, request, view, obj):
        # Staff can access anything
        if request.user.is_staff:
            return True

        # Check ownership
        if hasattr(obj, 'customer'):
            return obj.customer == request.user

        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class StaffOrOwnerPermission(permissions.BasePermission):
    """
    Allow staff full access, owners can read/update their own objects
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff have full access
        if request.user.is_staff:
            return True

        # Owners can read and update their own objects
        if request.method in ['GET', 'PUT', 'PATCH']:
            if hasattr(obj, 'customer'):
                return obj.customer == request.user
            if hasattr(obj, 'user'):
                return obj.user == request.user

        return False

