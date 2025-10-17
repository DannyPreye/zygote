from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Customer, CustomerGroup, Address


class CustomerGroupSerializer(serializers.ModelSerializer):
    """Customer group serializer"""
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomerGroup
        fields = [
            'id', 'name', 'description', 'auto_assign', 'assignment_rules',
            'discount_percentage', 'priority_support', 'free_shipping',
            'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_members_count(self, obj):
        return obj.customers.count()


class AddressSerializer(serializers.ModelSerializer):
    """Address serializer"""
    full_address = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = [
            'id', 'customer', 'address_type',
            'first_name', 'last_name', 'company', 'phone',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'is_default', 'full_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['customer', 'created_at', 'updated_at']

    def get_full_address(self, obj):
        parts = [
            obj.address_line1,
            obj.address_line2,
            obj.city,
            obj.state,
            obj.postal_code,
            obj.country
        ]
        return ', '.join([p for p in parts if p])


class AddressCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating addresses"""
    class Meta:
        model = Address
        fields = [
            'address_type', 'first_name', 'last_name', 'company', 'phone',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'is_default'
        ]

    def validate_phone(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        return value


class CustomerListSerializer(serializers.ModelSerializer):
    """Minimal customer serializer for lists"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'uuid', 'username', 'email', 'full_name',
            'phone', 'avatar', 'is_verified', 'is_vip',
            'loyalty_tier', 'total_orders', 'total_spent'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Detailed customer serializer"""
    full_name = serializers.SerializerMethodField()
    addresses = AddressSerializer(many=True, read_only=True)
    customer_groups = CustomerGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'uuid', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'phone_verified', 'date_of_birth', 'gender', 'avatar',
            'accepts_marketing_email', 'accepts_marketing_sms',
            'total_orders', 'total_spent', 'average_order_value', 'last_order_date',
            'loyalty_points', 'loyalty_tier', 'customer_groups',
            'preferred_language', 'preferred_currency',
            'source', 'is_verified', 'is_vip', 'is_active',
            'addresses', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'total_orders', 'total_spent', 'average_order_value',
            'last_order_date', 'loyalty_points', 'is_verified', 'is_vip',
            'created_at', 'updated_at'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profile updates"""
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'full_name', 'email', 'phone',
            'date_of_birth', 'gender', 'avatar',
            'accepts_marketing_email', 'accepts_marketing_sms',
            'preferred_language', 'preferred_currency'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def validate_email(self, value):
        user = self.context.get('request').user
        if Customer.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use")
        return value


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Customer
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value

    def validate_username(self, value):
        if Customer.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists")
        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        customer = Customer(**validated_data)
        customer.set_password(password)
        customer.save()
        return customer


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class CustomerStatsSerializer(serializers.Serializer):
    """Serializer for customer statistics"""
    total_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_order_date = serializers.DateTimeField()
    loyalty_points = serializers.IntegerField()
    loyalty_tier = serializers.CharField()

