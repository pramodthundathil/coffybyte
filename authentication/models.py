from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class TimeStampedModel(models.Model):
    """Base model with created_at and updated_at fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# =============== STORE & BRANCH MODELS ===============
class License(models.Model):
    """License model for managing store licenses"""
    LICENSE_TYPES = [
        ('trial', 'Trial'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_key = models.CharField(max_length=255, unique=True)
    license_type = models.CharField(max_length=50, choices=LICENSE_TYPES)
    issued_to = models.CharField(max_length=255)  # Store or owner name
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_users = models.IntegerField(default=5)  # Max users allowed for this license
    max_branches = models.IntegerField(default=1)  # Max branches allowed
    
    class Meta:
        db_table = 'licenses'
        
    def __str__(self):
        return f"{self.license_key} ({self.license_type})"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return self.is_active and not self.is_expired

class Store(TimeStampedModel):
    """Main store model - can have multiple branches"""
    BUSINESS_TYPES = [
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('retail', 'Retail'),
        ('bakery', 'Bakery'),
    ]
    
    SUBSCRIPTION_PLANS = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    store_code = models.CharField(max_length=50, unique=True)
    owner_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100, choices=BUSINESS_TYPES)
    subscription_plan = models.CharField(max_length=50, choices=SUBSCRIPTION_PLANS, default='basic')
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    license_key = models.OneToOneField(License, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Contact & Address
    logo_url = models.URLField(blank=True)
    primary_contact = models.JSONField(default=dict)  # {"phone": "", "email": ""}
    address = models.JSONField(default=dict)
    
    # Business Settings
    tax_settings = models.JSONField(default=dict)  # GST, VAT settings
    currency = models.CharField(max_length=3, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    business_hours = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'stores'
        
    def __str__(self):
        return f"{self.name} ({self.store_code})"
    
    def save(self, *args, **kwargs):
        if not self.subscription_expires_at and self.pk is None:
            # Set 1 year subscription for new stores
            self.subscription_expires_at = timezone.now() + timedelta(days=365)
        super().save(*args, **kwargs)
    
    @property
    def is_subscription_active(self):
        if not self.subscription_expires_at:
            return False
        return timezone.now() < self.subscription_expires_at
    
    @property
    def is_license_valid(self):
        if not self.license_key:
            return False
        return self.license_key.is_valid()
    
    def can_user_login(self, user_role):
        """Check if user can login based on subscription and license status"""
        if user_role == 'store_owner':
            return True  # Store owner can always login
        return self.is_subscription_active and self.is_license_valid

class Branch(TimeStampedModel):
    """Branch model - physical locations under a store"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=50)
    
    # Location & Contact
    address = models.JSONField(default=dict)
    contact_info = models.JSONField(default=dict)
    manager_contact = models.JSONField(default=dict)
    
    # Branch Settings
    is_main_branch = models.BooleanField(default=False)
    seating_capacity = models.IntegerField(null=True, blank=True)
    kitchen_printer_config = models.JSONField(default=dict)
    receipt_printer_config = models.JSONField(default=dict)
    pos_settings = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'branches'
        unique_together = ['store', 'branch_code']
        
    def __str__(self):
        return f"{self.store.name} - {self.name}"

class POSDevice(TimeStampedModel):
    """POS Terminal/Device model"""
    DEVICE_TYPES = [
        ('main_counter', 'Main Counter'),
        ('kitchen_display', 'Kitchen Display'),
        ('mobile', 'Mobile Device'),
        ('tablet', 'Tablet'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='pos_devices')
    device_name = models.CharField(max_length=255)
    device_code = models.CharField(max_length=50)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    
    # Device Info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=17, blank=True)
    printer_config = models.JSONField(default=dict)
    
    last_active_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'pos_devices'
        unique_together = ['branch', 'device_code']

# =============== USER MANAGEMENT ===============

class CustomUser(AbstractUser):
    """Extended User model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$')
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(unique=True)
    pin = models.CharField(max_length=6)  # Changed to CharField for better validation
    is_super_admin = models.BooleanField(default=False)  # Can access all stores
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    # Remove username requirement
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'

class StoreUser(TimeStampedModel):
    """Store-User relationship with roles"""
    STORE_ROLES = [
        ('store_owner', 'Store Owner'),
        ('store_manager', 'Store Manager'),
        ('branch_manager', 'Branch Manager'),
        ('cashier', 'Cashier'),
        ('chef', 'Chef'),
        ('waiter', 'Waiter'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_users')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='store_memberships')
    role = models.CharField(max_length=50, choices=STORE_ROLES)
    permissions = models.JSONField(default=list)  # List of permission strings
    
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='assigned_users')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'store_users'
        unique_together = ['store', 'user']

class BranchUser(TimeStampedModel):
    """Branch-User relationship for specific branch access"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='branch_users')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='branch_assignments')
    role = models.CharField(max_length=50, choices=StoreUser.STORE_ROLES)
    permissions = models.JSONField(default=list)
    
    # Shift settings
    can_open_shift = models.BooleanField(default=False)
    can_close_shift = models.BooleanField(default=False)
    max_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'branch_users'
        unique_together = ['branch', 'user']

# =============== PERMISSION MANAGEMENT ===============

class Permission(models.Model):
    """Permission model for granular access control"""
    PERMISSION_CATEGORIES = [
        ('sales', 'Sales'),
        ('inventory', 'Inventory'),
        ('reports', 'Reports'),
        ('users', 'User Management'),
        ('settings', 'Settings'),
        ('financial', 'Financial'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=PERMISSION_CATEGORIES)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'permissions'
        
    def __str__(self):
        return f"{self.name} ({self.codename})"

class RolePermission(models.Model):
    """Default permissions for each role"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=50, choices=StoreUser.STORE_ROLES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']