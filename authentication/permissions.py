from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from .models import Store, StoreUser, BranchUser

class IsStoreOwnerOrManager(permissions.BasePermission):
    """
    Permission to only allow store owners or managers to access store management
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        store_code = getattr(request, 'store_code', None) or request.data.get('store_code')
        if not store_code:
            return False
        
        try:
            store = Store.objects.get(store_code=store_code, is_active=True)
            store_user = StoreUser.objects.get(
                store=store, 
                user=request.user, 
                is_active=True
            )
            return store_user.role in ['store_owner', 'store_manager']
        except (Store.DoesNotExist, StoreUser.DoesNotExist):
            return False

class IsStoreOwner(permissions.BasePermission):
    """
    Permission to only allow store owners
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        store_code = getattr(request, 'store_code', None) or request.data.get('store_code')
        if not store_code:
            return False
        
        try:
            store = Store.objects.get(store_code=store_code, is_active=True)
            store_user = StoreUser.objects.get(
                store=store, 
                user=request.user, 
                is_active=True
            )
            return store_user.role == 'store_owner'
        except (Store.DoesNotExist, StoreUser.DoesNotExist):
            return False

class HasStoreAccess(permissions.BasePermission):
    """
    Permission to check if user has access to a specific store
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Super admin has access to all stores
        if request.user.is_super_admin:
            return True
        
        store_code = getattr(request, 'store_code', None) or request.data.get('store_code')
        if not store_code:
            return False
        
        try:
            store = Store.objects.get(store_code=store_code, is_active=True)
            store_user = StoreUser.objects.get(
                store=store, 
                user=request.user, 
                is_active=True
            )
            
            # Check if user can login based on subscription/license
            if not store.can_user_login(store_user.role):
                if store_user.role != 'store_owner':
                    raise PermissionDenied('Store subscription or license has expired. Only store owner can access.')
            
            # Store the store and store_user in request for later use
            request.store = store
            request.store_user = store_user
            
            return True
        except (Store.DoesNotExist, StoreUser.DoesNotExist):
            return False

class HasBranchAccess(permissions.BasePermission):
    """
    Permission to check if user has access to a specific branch
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # First check store access
        if not HasStoreAccess().has_permission(request, view):
            return False
        
        branch_id = view.kwargs.get('branch_id') or request.data.get('branch_id')
        if not branch_id:
            return True  # If no specific branch, store access is enough
        
        try:
            branch_user = BranchUser.objects.get(
                branch_id=branch_id,
                user=request.user,
                is_active=True
            )
            request.branch_user = branch_user
            return True
        except BranchUser.DoesNotExist:
            # Check if user is store owner/manager (they have access to all branches)
            return request.store_user.role in ['store_owner', 'store_manager']

class HasPermission(permissions.BasePermission):
    """
    Permission to check specific permissions
    """
    def __init__(self, required_permission):
        self.required_permission = required_permission
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Super admin has all permissions
        if request.user.is_super_admin:
            return True
        
        # Check if user has store access first
        if not hasattr(request, 'store_user'):
            return False
        
        store_user = request.store_user
        
        # Store owner has all permissions
        if store_user.role == 'store_owner':
            return True
        
        # Check if permission is in user's permission list
        return (
            'all' in store_user.permissions or 
            self.required_permission in store_user.permissions
        )

def require_permission(permission_name):
    """
    Decorator to require specific permission
    """
    def decorator(view_class):
        original_permission_classes = getattr(view_class, 'permission_classes', [])
        view_class.permission_classes = original_permission_classes + [
            lambda: HasPermission(permission_name)
        ]
        return view_class
    return decorator

# Permission constants
class Permissions:
    # User Management
    CREATE_USERS = 'create_users'
    EDIT_USERS = 'edit_users'
    DELETE_USERS = 'delete_users'
    VIEW_USERS = 'view_users'
    
    # Sales
    CREATE_ORDERS = 'create_orders'
    EDIT_ORDERS = 'edit_orders'
    DELETE_ORDERS = 'delete_orders'
    VIEW_ORDERS = 'view_orders'
    APPLY_DISCOUNTS = 'apply_discounts'
    REFUND_ORDERS = 'refund_orders'
    
    # Inventory
    MANAGE_INVENTORY = 'manage_inventory'
    VIEW_INVENTORY = 'view_inventory'
    STOCK_ADJUSTMENTS = 'stock_adjustments'
    
    # Reports
    VIEW_SALES_REPORTS = 'view_sales_reports'
    VIEW_INVENTORY_REPORTS = 'view_inventory_reports'
    VIEW_USER_REPORTS = 'view_user_reports'
    EXPORT_REPORTS = 'export_reports'
    
    # Settings
    MANAGE_STORE_SETTINGS = 'manage_store_settings'
    MANAGE_BRANCH_SETTINGS = 'manage_branch_settings'
    MANAGE_POS_DEVICES = 'manage_pos_devices'
    
    # Financial
    VIEW_FINANCIAL_DATA = 'view_financial_data'
    MANAGE_PAYMENTS = 'manage_payments'
    
    # Shifts
    OPEN_SHIFT = 'open_shift'
    CLOSE_SHIFT = 'close_shift'
    VIEW_SHIFT_REPORTS = 'view_shift_reports'

# Default permissions for each role
DEFAULT_PERMISSIONS = {
    'store_owner': ['all'],
    'store_manager': [
        Permissions.CREATE_USERS, Permissions.EDIT_USERS, Permissions.VIEW_USERS,
        Permissions.CREATE_ORDERS, Permissions.EDIT_ORDERS, Permissions.VIEW_ORDERS,
        Permissions.APPLY_DISCOUNTS, Permissions.REFUND_ORDERS,
        Permissions.MANAGE_INVENTORY, Permissions.VIEW_INVENTORY, Permissions.STOCK_ADJUSTMENTS,
        Permissions.VIEW_SALES_REPORTS, Permissions.VIEW_INVENTORY_REPORTS,
        Permissions.VIEW_USER_REPORTS, Permissions.EXPORT_REPORTS,
        Permissions.MANAGE_BRANCH_SETTINGS, Permissions.MANAGE_POS_DEVICES,
        Permissions.VIEW_FINANCIAL_DATA, Permissions.MANAGE_PAYMENTS,
        Permissions.OPEN_SHIFT, Permissions.CLOSE_SHIFT, Permissions.VIEW_SHIFT_REPORTS,
    ],
    'branch_manager': [
        Permissions.VIEW_USERS,
        Permissions.CREATE_ORDERS, Permissions.EDIT_ORDERS, Permissions.VIEW_ORDERS,
        Permissions.APPLY_DISCOUNTS, Permissions.REFUND_ORDERS,
        Permissions.MANAGE_INVENTORY, Permissions.VIEW_INVENTORY, Permissions.STOCK_ADJUSTMENTS,
        Permissions.VIEW_SALES_REPORTS, Permissions.VIEW_INVENTORY_REPORTS,
        Permissions.MANAGE_POS_DEVICES,
        Permissions.VIEW_FINANCIAL_DATA, Permissions.MANAGE_PAYMENTS,
        Permissions.OPEN_SHIFT, Permissions.CLOSE_SHIFT, Permissions.VIEW_SHIFT_REPORTS,
    ],
    'cashier': [
        Permissions.CREATE_ORDERS, Permissions.VIEW_ORDERS,
        Permissions.APPLY_DISCOUNTS, Permissions.VIEW_INVENTORY,
        Permissions.MANAGE_PAYMENTS,
    ],
    'chef': [
        Permissions.VIEW_ORDERS, Permissions.VIEW_INVENTORY,
    ],
    'waiter': [
        Permissions.CREATE_ORDERS, Permissions.VIEW_ORDERS, Permissions.VIEW_INVENTORY,
    ],
}

