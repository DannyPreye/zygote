"""
Authentication Serializers with Enhanced Security
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import TwoFactorAuth, LoginAttempt, SessionActivity
import pyotp
import re

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional claims"""

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add custom claims
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'full_name': self.user.get_full_name(),
            'is_verified': self.user.is_verified,
            'is_vip': self.user.is_vip,
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims to token
        token['username'] = user.username
        token['email'] = user.email
        token['is_verified'] = user.is_verified

        return token


class LoginSerializer(serializers.Serializer):
    """Secure login serializer"""
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    two_factor_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')
        two_factor_code = attrs.get('two_factor_code')

        if not username and not email:
            raise serializers.ValidationError("Must provide username or email")

        # Use email as username if provided
        if email and not username:
            username = email

        request = self.context.get('request')
        user = authenticate(request=request, username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # Check if 2FA is enabled
        if hasattr(user, 'two_factor') and user.two_factor.is_enabled:
            if not two_factor_code:
                raise serializers.ValidationError({
                    'two_factor_required': True,
                    'message': 'Two-factor authentication code required'
                })

            # Verify 2FA code
            totp = pyotp.TOTP(user.two_factor.secret_key)
            if not totp.verify(two_factor_code, valid_window=1):
                raise serializers.ValidationError("Invalid two-factor authentication code")

        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    """Secure registration serializer with strong password requirements"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")

        # Basic email format validation
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
            raise serializers.ValidationError("Invalid email format")

        return value.lower()

    def validate_username(self, value):
        """Validate username format and uniqueness"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists")

        # Username must be alphanumeric with optional underscores
        if not re.match(r'^[\w]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, and underscores"
            )

        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters")

        return value.lower()

    def validate_password(self, value):
        """Additional password validation"""
        # Check for common patterns
        if value.lower() in ['password', '12345678', 'qwerty']:
            raise serializers.ValidationError("Password is too common")

        # Require at least one uppercase, one lowercase, one digit
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")

        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character")

        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match"})
        return attrs

    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password2')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True  # Set to False if email verification is required
        user.save()

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset"""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if email exists"""
        if not User.objects.filter(email=value).exists():
            # Don't reveal if email exists for security
            pass
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset with token"""
    token = serializers.UUIDField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match"})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Change password for authenticated user"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """Verify old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match"})

        # Ensure new password is different from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from old password"}
            )

        return attrs


class TwoFactorSetupSerializer(serializers.Serializer):
    """Setup two-factor authentication"""
    def create(self, validated_data):
        user = self.context['request'].user

        # Generate secret key
        secret = pyotp.random_base32()

        # Generate backup codes
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]

        # Create or update 2FA settings
        two_factor, created = TwoFactorAuth.objects.get_or_create(user=user)
        two_factor.secret_key = secret
        two_factor.backup_codes = backup_codes
        two_factor.is_enabled = False  # Not enabled until verified
        two_factor.save()

        # Generate QR code URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='Multi-Tenant Store'
        )

        return {
            'secret': secret,
            'qr_code_uri': provisioning_uri,
            'backup_codes': backup_codes
        }


class TwoFactorVerifySerializer(serializers.Serializer):
    """Verify and enable two-factor authentication"""
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        """Verify the code"""
        user = self.context['request'].user

        if not hasattr(user, 'two_factor'):
            raise serializers.ValidationError("2FA not set up")

        totp = pyotp.TOTP(user.two_factor.secret_key)
        if not totp.verify(value, valid_window=1):
            raise serializers.ValidationError("Invalid code")

        return value

    def save(self):
        """Enable 2FA"""
        user = self.context['request'].user
        user.two_factor.is_enabled = True
        user.two_factor.save()
        return user.two_factor


class TwoFactorDisableSerializer(serializers.Serializer):
    """Disable two-factor authentication"""
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_password(self, value):
        """Verify password before disabling 2FA"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password")
        return value


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Login attempt history"""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'username', 'ip_address', 'user_agent',
            'success', 'failure_reason', 'country', 'city', 'timestamp'
        ]


class SessionActivitySerializer(serializers.ModelSerializer):
    """Active session information"""
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = SessionActivity
        fields = [
            'id', 'session_key', 'ip_address', 'user_agent',
            'device_type', 'browser', 'location',
            'created_at', 'last_activity', 'is_active', 'is_current'
        ]

    def get_is_current(self, obj):
        """Check if this is the current session"""
        request = self.context.get('request')
        if request and hasattr(request, 'session'):
            return obj.session_key == request.session.session_key
        return False


class LogoutSerializer(serializers.Serializer):
    """Logout serializer"""
    refresh_token = serializers.CharField(required=False)
    all_devices = serializers.BooleanField(default=False)


class EmailVerificationSerializer(serializers.Serializer):
    """Email verification"""
    token = serializers.UUIDField()

