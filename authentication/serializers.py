from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from .models import (
    CustomUser, Store, Branch, StoreUser, BranchUser, 
    License, POSDevice, Permission, RolePermission
)
import secrets
import string

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 
            'pin', 'password', 'confirm_password', 'is_active', 'last_login_at'
        ]
        extra_kwargs = {
            'pin': {'write_only': True},
            'password': {'write_only': True},
            'last_login_at': {'read_only': True}
        }
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def validate(self, attrs):
        if 'password' in attrs and 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_pin(self, value):
        if value and (not str(value).isdigit() or len(str(value)) != 6):
            raise serializers.ValidationError("PIN must be exactly 6 digits")
        return str(value)
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    pin = serializers.CharField(max_length=6)
    # store_code = serializers.CharField(required=False)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        pin = attrs.get('pin')
        # store_code = attrs.get('store_code')
        
        if not email or not password or not pin:
            raise serializers.ValidationError('Email, password, and PIN are required')
        
        # Authenticate user
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password')
        
        # Validate PIN
        if user.pin != pin:
            raise serializers.ValidationError('Invalid PIN')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        
      
        try:
            store_user = StoreUser.objects.get(
                    user=user, 
                    role='store_owner', 
                    is_active=True
                )
            attrs['store'] = store_user.store
            attrs['store_user'] = store_user
            # Check if user can login based on subscription/license
            if not store_user.store.can_user_login(store_user.role):
                if store_user.role != 'store_owner':
                    raise serializers.ValidationError(
                        'Store subscription or license has expired. Only store owner can access.'
                    )
            
            attrs['store'] = store_user.store
            attrs['store_user'] = store_user
            
        except Store.DoesNotExist:
            attrs['store'] = []
            attrs['store_user'] = []
        except:
            attrs['store'] = []
            attrs['store_user'] = []
        
        # else:
        #     # Check if user is a store owner (can login without store_code)
        #     try:
        #         store_user = StoreUser.objects.get(
        #             user=user, 
        #             role='store_owner', 
        #             is_active=True
        #         )
        #         attrs['store'] = store_user.store
        #         attrs['store_user'] = store_user
        #     except StoreUser.DoesNotExist:
        #         if user.is_super_admin:
        #             pass
        #         else:
        #             if not store_code:
        #                 raise serializers.ValidationError('Store code required for non-owner users')
            
        attrs['user'] = user
        return attrs

class LicenseSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = License
        fields = '__all__'
        read_only_fields = ['id', 'license_key', 'issued_at']
    
    def get_days_remaining(self, obj):
        if obj.expires_at:
            remaining = obj.expires_at - timezone.now()
            return max(0, remaining.days)
        return None

class StoreSerializer(serializers.ModelSerializer):
    is_subscription_active = serializers.ReadOnlyField()
    is_license_valid = serializers.ReadOnlyField()
    license_info = LicenseSerializer(source='license_key', read_only=True)
    total_users = serializers.SerializerMethodField()
    total_branches = serializers.SerializerMethodField()
    subscription_days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'store_code', 'owner_name', 'business_type',
            'subscription_plan', 'subscription_expires_at', 'status',
            'logo_url', 'primary_contact', 'address', 'tax_settings',
            'currency', 'timezone', 'business_hours', 'is_active',
            'is_subscription_active', 'is_license_valid', 'license_info',
            'total_users', 'total_branches', 'subscription_days_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'store_code', 'created_at', 'updated_at']
    
    def get_total_users(self, obj):
        return obj.store_users.filter(is_active=True).count()
    
    def get_total_branches(self, obj):
        return obj.branches.filter(is_active=True).count()
    
    def get_subscription_days_remaining(self, obj):
        if obj.subscription_expires_at:
            remaining = obj.subscription_expires_at - timezone.now()
            return max(0, remaining.days)
        return None

class StoreRegistrationSerializer(serializers.Serializer):
    # Store Info
    store_name = serializers.CharField(max_length=255)
    store_code = serializers.CharField(max_length=50)
    owner_name = serializers.CharField(max_length=255)
    business_type = serializers.ChoiceField(choices=Store.BUSINESS_TYPES)
    subscription_plan = serializers.ChoiceField(choices=Store.SUBSCRIPTION_PLANS, default='basic')
    
    # Contact & Address
    logo_url = serializers.URLField(required=False, allow_blank=True)
    primary_contact = serializers.JSONField(default=dict)
    address = serializers.JSONField(default=dict)
    currency = serializers.CharField(max_length=3, default='USD')
    timezone = serializers.CharField(max_length=50, default='UTC')
    tax_settings = serializers.JSONField(default=dict)
    business_hours = serializers.JSONField(default=dict)
    
    # Owner Info
    owner_email = serializers.EmailField()
    owner_phone = serializers.CharField(max_length=17, required=False, allow_blank=True)
    owner_password = serializers.CharField(validators=[validate_password])
    owner_pin = serializers.CharField(max_length=6)
    
    # Branch Info
    branch_name = serializers.CharField(max_length=255, default='Main Branch')
    branch_address = serializers.JSONField(default=dict)
    
    def validate_store_code(self, value):
        if Store.objects.filter(store_code=value.upper()).exists():
            raise serializers.ValidationError('Store code already exists')
        return value.upper()
    
    def validate_owner_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value
    
    def validate_owner_pin(self, value):
        if not str(value).isdigit() or len(str(value)) != 6:
            raise serializers.ValidationError('PIN must be exactly 6 digits')
        return str(value)
    
    def generate_license_key(self):
        """Generate a unique license key"""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            key = ''.join(secrets.choice(alphabet) for _ in range(16))
            formatted_key = '-'.join([key[i:i+4] for i in range(0, 16, 4)])
            if not License.objects.filter(license_key=formatted_key).exists():
                return formatted_key
    
    @transaction.atomic
    def create(self, validated_data):
        # Create owner user
        owner_data = {
            'email': validated_data['owner_email'],
            'first_name': validated_data['owner_name'].split()[0],
            'last_name': ' '.join(validated_data['owner_name'].split()[1:]) if len(validated_data['owner_name'].split()) > 1 else '',
            'phone': validated_data.get('owner_phone', ''),
            'pin': validated_data['owner_pin'],
        }
        owner = CustomUser(**owner_data)
        owner.set_password(validated_data['owner_password'])
        owner.save()
        
        # Create license
        license_key = self.generate_license_key()
        license_obj = License.objects.create(
            license_key=license_key,
            license_type='standard',
            issued_to=validated_data['owner_name'],
            expires_at=timezone.now() + timezone.timedelta(days=365)
        )
        
        # Create store
        store_data = {
            'name': validated_data['store_name'],
            'store_code': validated_data['store_code'],
            'owner_name': validated_data['owner_name'],
            'business_type': validated_data['business_type'],
            'subscription_plan': validated_data.get('subscription_plan', 'basic'),
            'logo_url': validated_data.get('logo_url', ''),
            'primary_contact': validated_data.get('primary_contact', {}),
            'address': validated_data.get('address', {}),
            'currency': validated_data.get('currency', 'USD'),
            'timezone': validated_data.get('timezone', 'UTC'),
            'tax_settings': validated_data.get('tax_settings', {}),
            'business_hours': validated_data.get('business_hours', {}),
            'license_key': license_obj
        }
        store = Store.objects.create(**store_data)
        
        # Create main branch
        branch = Branch.objects.create(
            store=store,
            name=validated_data.get('branch_name', 'Main Branch'),
            branch_code='MAIN',
            address=validated_data.get('branch_address', {}),
            is_main_branch=True
        )
        
        # Assign owner to store
        StoreUser.objects.create(
            store=store,
            user=owner,
            role='store_owner',
            permissions=['all'],
            assigned_by=owner
        )
        
        # Assign owner to branch
        BranchUser.objects.create(
            branch=branch,
            user=owner,
            role='store_owner',
            permissions=['all'],
            can_open_shift=True,
            can_close_shift=True,
            max_discount_percent=100
        )
        
        return {
            'store': store,
            'owner': owner,
            'branch': branch,
            'license': license_obj
        }

class BranchSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.store_code', read_only=True)
    total_users = serializers.SerializerMethodField()
    total_devices = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'store', 'name', 'branch_code', 'address', 'contact_info',
            'manager_contact', 'is_main_branch', 'seating_capacity',
            'kitchen_printer_config', 'receipt_printer_config', 'pos_settings',
            'is_active', 'store_name', 'store_code', 'total_users', 'total_devices',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'store', 'created_at', 'updated_at']
    
    def get_total_users(self, obj):
        return obj.branch_users.filter(is_active=True).count()
    
    def get_total_devices(self, obj):
        return obj.pos_devices.filter(is_active=True).count()
    
    def validate_branch_code(self, value):
        store = self.context.get('store')
        if store and Branch.objects.filter(store=store, branch_code=value.upper()).exists():
            if not self.instance or self.instance.branch_code != value.upper():
                raise serializers.ValidationError('Branch code already exists in this store')
        return value.upper()

class StoreUserSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_code = serializers.CharField(source='store.store_code', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = StoreUser
        fields = [
            'id', 'store', 'user', 'role', 'role_display', 'permissions', 'is_active',
            'assigned_by', 'assigned_at', 'created_at', 'updated_at',
            'user_info', 'store_name', 'store_code', 'assigned_by_name'
        ]
        read_only_fields = ['id', 'store', 'assigned_by', 'assigned_at', 'created_at', 'updated_at']

class StoreUserCreateSerializer(serializers.ModelSerializer):
    # User creation fields
    user_email = serializers.EmailField(write_only=True)
    user_password = serializers.CharField(write_only=True, validators=[validate_password])
    user_first_name = serializers.CharField(write_only=True, max_length=30)
    user_last_name = serializers.CharField(write_only=True, max_length=30)
    user_phone = serializers.CharField(write_only=True, max_length=17, required=False, allow_blank=True)
    user_pin = serializers.CharField(write_only=True, max_length=6)
    
    # Additional fields for response
    user_info = UserSerializer(source='user', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    
    class Meta:
        model = StoreUser
        fields = [
            'id', 'role', 'permissions', 'is_active',
            'user_email', 'user_password', 'user_first_name', 'user_last_name', 
            'user_phone', 'user_pin',
            'user_info', 'store_name', 'assigned_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_user_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email already exists')
        return value
    
    def validate_user_pin(self, value):
        if not str(value).isdigit() or len(str(value)) != 6:
            raise serializers.ValidationError('PIN must be exactly 6 digits')
        return str(value)
    
    def validate_role(self, value):
        # Prevent non-owners from creating other store owners
        request = self.context.get('request')
        if request and value == 'store_owner':
            try:
                current_store_user = StoreUser.objects.get(
                    user=request.user,
                    is_active=True
                )
                if current_store_user.role != 'store_owner':
                    raise serializers.ValidationError('Only store owners can create other store owners')
            except StoreUser.DoesNotExist:
                raise serializers.ValidationError('Invalid user context')
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        # Extract user data
        user_data = {
            'email': validated_data.pop('user_email'),
            'first_name': validated_data.pop('user_first_name'),
            'last_name': validated_data.pop('user_last_name'),
            'phone': validated_data.pop('user_phone', ''),
            'pin': validated_data.pop('user_pin'),
        }
        password = validated_data.pop('user_password')
        
        # Create user
        user = CustomUser(**user_data)
        user.set_password(password)
        user.save()
        
        # Create store user
        store_user = StoreUser.objects.create(
            user=user,
            assigned_by=self.context['request'].user,
            **validated_data
        )
        
        return store_user

class BranchUserSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_code = serializers.CharField(source='branch.branch_code', read_only=True)
    store_name = serializers.CharField(source='branch.store.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = BranchUser
        fields = [
            'id', 'branch', 'user', 'role', 'role_display', 'permissions',
            'can_open_shift', 'can_close_shift', 'max_discount_percent', 'is_active',
            'user_info', 'branch_name', 'branch_code', 'store_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class POSDeviceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    branch_code = serializers.CharField(source='branch.branch_code', read_only=True)
    store_name = serializers.CharField(source='branch.store.name', read_only=True)
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = POSDevice
        fields = [
            'id', 'branch', 'device_name', 'device_code', 'device_type', 'device_type_display',
            'ip_address', 'mac_address', 'printer_config', 'last_active_at', 'is_active',
            'branch_name', 'branch_code', 'store_name', 'is_online',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_online(self, obj):
        if obj.last_active_at:
            # Consider device online if active within last 5 minutes
            threshold = timezone.now() - timezone.timedelta(minutes=5)
            return obj.last_active_at > threshold
        return False
    
    def validate_device_code(self, value):
        branch = self.context.get('branch') or (self.instance.branch if self.instance else None)
        if branch and POSDevice.objects.filter(branch=branch, device_code=value.upper()).exists():
            if not self.instance or self.instance.device_code != value.upper():
                raise serializers.ValidationError('Device code already exists in this branch')
        return value.upper()

class PermissionSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Permission
        fields = [
            'id', 'name', 'codename', 'description', 'category', 'category_display', 'is_active'
        ]

class LicenseActivationSerializer(serializers.Serializer):
    license_key = serializers.CharField(max_length=255)
    store_code = serializers.CharField(max_length=50, required=False)  # Made optional for auto-detection
    
    def validate(self, attrs):
        license_key = attrs.get('license_key')
        store_code = attrs.get('store_code')
        
        # Get store from context if not provided
        if not store_code:
            request = self.context.get('request')
            if request:
                try:
                    store_user = StoreUser.objects.get(
                        user=request.user,
                        role='store_owner',
                        is_active=True
                    )
                    store = store_user.store
                    attrs['store_code'] = store.store_code
                except StoreUser.DoesNotExist:
                    raise serializers.ValidationError('Store owner context required')
            else:
                raise serializers.ValidationError('Store code required')
        
        try:
            store = Store.objects.get(store_code=attrs['store_code'], is_active=True)
        except Store.DoesNotExist:
            raise serializers.ValidationError('Invalid store code')
        
        try:
            license_obj = License.objects.get(license_key=license_key)
        except License.DoesNotExist:
            raise serializers.ValidationError('Invalid license key')
        
        if not license_obj.is_valid():
            raise serializers.ValidationError('License is expired or inactive')
        
        # Check if license is already assigned to a different store
        if hasattr(license_obj, 'store') and license_obj.store and license_obj.store != store:
            raise serializers.ValidationError('License is already assigned to another store')
        
        attrs['store'] = store
        attrs['license'] = license_obj
        return attrs
    
    def save(self):
        store = self.validated_data['store']
        license_obj = self.validated_data['license']
        
        store.license_key = license_obj
        store.subscription_expires_at = license_obj.expires_at
        store.status = 'active'
        store.save()
        
        return store

class StoreStatusSerializer(serializers.Serializer):
    """Serializer for store status information"""
    store_code = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    status = serializers.CharField()
    subscription = serializers.DictField()
    license = serializers.DictField()
    can_login = serializers.BooleanField()

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_branches = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_devices = serializers.IntegerField()
    subscription_status = serializers.DictField()
    license_status = serializers.DictField()

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    current_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value

class ChangePinSerializer(serializers.Serializer):
    """Serializer for changing user PIN"""
    current_pin = serializers.CharField(max_length=6)
    new_pin = serializers.CharField(max_length=6)
    
    def validate_current_pin(self, value):
        user = self.context['request'].user
        if user.pin != value:
            raise serializers.ValidationError('Current PIN is incorrect')
        return value
    
    def validate_new_pin(self, value):
        if not str(value).isdigit() or len(str(value)) != 6:
            raise serializers.ValidationError('PIN must be exactly 6 digits')
        return str(value)