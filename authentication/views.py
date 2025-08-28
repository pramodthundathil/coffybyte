from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.types import OpenApiTypes
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    CustomUser, Store, Branch, StoreUser, BranchUser, 
    License, POSDevice, Permission
)
from .serializers import (
    UserSerializer, LoginSerializer, StoreSerializer, StoreRegistrationSerializer,
    BranchSerializer, StoreUserSerializer, StoreUserCreateSerializer,
    BranchUserSerializer, POSDeviceSerializer, LicenseSerializer,
    LicenseActivationSerializer, PermissionSerializer
)
from .permissions import (
    IsStoreOwner, IsStoreOwnerOrManager, HasStoreAccess, 
    HasBranchAccess, HasPermission, Permissions, DEFAULT_PERMISSIONS
)

# =============== AUTHENTICATION VIEWS ===============

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT authentication endpoint with PIN validation and automatic store identification.
    
    For store owners, automatically identifies and loads their store context.
    For other users, requires store_code to specify which store to access.
    """
    serializer_class = LoginSerializer
    
    @extend_schema(
        summary="User Login with JWT Token",
        description="""
        Authenticate user with email, password, and PIN. 
        - Store owners: Automatically identifies their store (no store_code needed)
        - Other users: Must provide store_code to specify which store to access
        - Returns JWT tokens with store context and user permissions
        """,
        request=LoginSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string', 'description': 'JWT refresh token'},
                    'access': {'type': 'string', 'description': 'JWT access token'},
                    'user': {'type': 'object', 'description': 'User information'},
                    'store': {'type': 'object', 'description': 'Store information'},
                    'role': {'type': 'string', 'description': 'User role in the store'},
                    'permissions': {'type': 'array', 'items': {'type': 'string'}, 'description': 'User permissions'},
                }
            },
            400: {'description': 'Invalid credentials or validation errors'},
            403: {'description': 'Store subscription expired (non-owners only)'}
        },
        examples=[
            OpenApiExample(
                'Store Owner Login',
                summary='Store owner login (auto-detects store)',
                description='Store owners only need email, password, and PIN',
                value={
                    "email": "owner@restaurant.com",
                    "password": "SecurePassword123!",
                    "pin": "123456"
                }
            ),
            OpenApiExample(
                'Employee Login',
                summary='Employee login (requires store_code)',
                description='Employees must specify which store to access',
                value={
                    "email": "cashier@restaurant.com",
                    "password": "SecurePassword123!",
                    "pin": "654321",
                    "store_code": "REST001"
                }
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        # store = serializer.validated_data.get('store')
        # store_user = serializer.validated_data.get('store_user')
        
        # If no store provided and user is store owner, auto-detect store
        # if not store:
        #     try:
        #         store_user = StoreUser.objects.get(
        #             user=user, 
        #             role='store_owner', 
        #             is_active=True
        #         )
        #         store = store_user.store
        #     except StoreUser.DoesNotExist:
        #         return Response({
        #             'error': 'Store code required for non-owner users'
        #         }, status=status.HTTP_400_BAD_REQUEST)
        attrs = {}
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
        
        # Update last login
        user.last_login_at = timezone.now()
        user.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        try:
            # Add custom claims
            refresh['store_code'] = store_user.store.store_code
            refresh['store_id'] = str(store_user.store.id)
            refresh['role'] = store_user.role
            refresh['permissions'] = store_user.permissions
        except:
            pass 

        try:
            store = StoreSerializer(store_user.store).data,
            role = store_user.role,
            permissions = store_user.permissions,
        except:
            store = []
            role = "not available"
            permissions = {}


        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
            
            'store': store,
            'role': role,
            'permissions': permissions,
            
            
        }, status=status.HTTP_200_OK)

@extend_schema(
    summary="Register New Store",
    description="""
    Register a new store with owner account. Creates:
    - Store with 1-year subscription
    - License key
    - Owner user account
    - Main branch
    - Store and branch user assignments
    """,
    request=StoreRegistrationSerializer,
    responses={
        201: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'store': {'type': 'object'},
                'license_key': {'type': 'string'},
                'owner': {'type': 'object'},
            }
        },
        400: {'description': 'Validation errors'}
    },
    examples=[
        OpenApiExample(
            'Store Registration',
            summary='Complete store registration',
            value={
                "store_name": "My Restaurant",
                "store_code": "REST001",
                "owner_name": "John Doe",
                "business_type": "restaurant",
                "subscription_plan": "premium",
                "primary_contact": {
                    "phone": "+1234567890",
                    "email": "contact@myrestaurant.com"
                },
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "state": "NY",
                    "zip": "10001"
                },
                "owner_email": "john@myrestaurant.com",
                "owner_phone": "+1234567890",
                "owner_password": "SecurePassword123!",
                "owner_pin": "123456",
                "branch_name": "Main Branch"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_store(request):
    serializer = StoreRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        
        return Response({
            'message': 'Store registered successfully',
            'store': StoreSerializer(result['store']).data,
            'license_key': result['license'].license_key,
            'owner': UserSerializer(result['owner']).data,
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Activate Store License",
    description="""
    Activate a license key for the current store. 
    Only store owners can activate licenses.
    Automatically identifies the owner's store.
    """,
    request=LicenseActivationSerializer,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'store': {'type': 'object'},
            }
        },
        400: {'description': 'Invalid license key'},
        403: {'description': 'Only store owners can activate licenses'}
    },
    examples=[
        OpenApiExample(
            'License Activation',
            value={
                "license_key": "XXXX-XXXX-XXXX-XXXX"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def activate_license(request):
    # Auto-identify store owner's store
    try:
        store_user = StoreUser.objects.get(
            user=request.user, 
            role='store_owner', 
            is_active=True
        )
        store = store_user.store
    except StoreUser.DoesNotExist:
        return Response({
            'error': 'Only store owners can activate licenses'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Add store_code to request data for serializer validation
    data = request.data.copy()
    data['store_code'] = store.store_code
    
    serializer = LicenseActivationSerializer(data=data)
    if serializer.is_valid():
        activated_store = serializer.save()
        return Response({
            'message': 'License activated successfully',
            'store': StoreSerializer(activated_store).data,
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =============== STORE MANAGEMENT VIEWS ===============

class StoreListView(generics.ListAPIView):
    """
    List stores based on user permissions.
    - Super admins: See all stores
    - Store owners/users: See only their stores
    """
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="List User Stores",
        description="""
        List stores accessible to the authenticated user:
        - Super admins see all stores
        - Store owners see their stores
        - Other users see stores they have access to
        """,
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/Store'}},
        }
    )
    def get_queryset(self):
        if self.request.user.is_super_admin:
            return Store.objects.all()
        return Store.objects.filter(
            store_users__user=self.request.user,
            store_users__is_active=True
        ).distinct()

class MyStoreDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user's store details.
    Automatically identifies the store based on user's ownership/membership.
    """
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get My Store Details",
        description="""
        Retrieve details of the current user's store.
        - For store owners: Returns their store
        - For employees: Returns the store they're currently accessing
        """,
        responses={
            200: {'$ref': '#/components/schemas/Store'},
            404: {'description': 'Store not found or no access'}
        }
    )
    def get_object(self):
        # Try to get from JWT token first
        if hasattr(self.request, 'user') and hasattr(self.request.user, 'token'):
            store_id = getattr(self.request.user.token, 'store_id', None)
            if store_id:
                return get_object_or_404(Store, id=store_id)
        
        # Fallback to store owner lookup
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                role='store_owner',
                is_active=True
            )
            return store_user.store
        except StoreUser.DoesNotExist:
            # If not owner, get first accessible store
            store_user = StoreUser.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
            if store_user:
                return store_user.store
            
        return None

    @extend_schema(
        summary="Update My Store",
        description="Update store details. Only store owners can modify store information.",
        request=StoreSerializer,
        responses={
            200: {'$ref': '#/components/schemas/Store'},
            403: {'description': 'Only store owners can update store details'}
        }
    )
    def put(self, request, *args, **kwargs):
        store = self.get_object()
        if not store:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is store owner
        try:
            StoreUser.objects.get(
                user=request.user,
                store=store,
                role='store_owner',
                is_active=True
            )
        except StoreUser.DoesNotExist:
            return Response({
                'error': 'Only store owners can update store details'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().put(request, *args, **kwargs)

# =============== BRANCH MANAGEMENT VIEWS ===============

class BranchListCreateView(generics.ListCreateAPIView):
    """
    List and create branches for the current user's store.
    Automatically identifies the store context.
    """
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="List My Store Branches",
        description="List all branches for the current user's store",
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/Branch'}},
        }
    )
    def get_queryset(self):
        # Get user's store
        store_user = StoreUser.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        if not store_user:
            return Branch.objects.none()
        
        return Branch.objects.filter(
            store=store_user.store,
            is_active=True
        )
    
    @extend_schema(
        summary="Create New Branch",
        description="""
        Create a new branch for the current store.
        Only store owners and managers can create branches.
        """,
        request=BranchSerializer,
        responses={
            201: {'$ref': '#/components/schemas/Branch'},
            403: {'description': 'Only store owners/managers can create branches'}
        }
    )
    def perform_create(self, serializer):
        # Get user's store
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can create branches')
        
        store = store_user.store
        
        # Check license limits
        if store.license_key:
            current_branches = store.branches.filter(is_active=True).count()
            if current_branches >= store.license_key.max_branches:
                raise ValidationError(
                    f'Maximum branches ({store.license_key.max_branches}) reached for current license'
                )
        
        serializer.save(store=store)

class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific branch.
    Only accessible to users of the same store.
    """
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'branch_id'
    
    @extend_schema(
        summary="Get Branch Details",
        description="Retrieve details of a specific branch",
        responses={
            200: {'$ref': '#/components/schemas/Branch'},
            404: {'description': 'Branch not found'}
        }
    )
    def get_queryset(self):
        # Get user's accessible stores
        user_stores = Store.objects.filter(
            store_users__user=self.request.user,
            store_users__is_active=True
        )
        return Branch.objects.filter(store__in=user_stores)
    
    @extend_schema(
        summary="Update Branch",
        description="Update branch details. Only store owners/managers allowed.",
        request=BranchSerializer
    )
    def perform_update(self, serializer):
        branch = self.get_object()
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can update branches')
        
        serializer.save()
    
    @extend_schema(
        summary="Delete Branch",
        description="Delete a branch. Only store owners allowed.",
    )
    def perform_destroy(self, instance):
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=instance.store,
                role='store_owner',
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners can delete branches')
        
        instance.is_active = False
        instance.save()

# =============== USER MANAGEMENT VIEWS ===============

class StoreUserListCreateView(generics.ListCreateAPIView):
    """
    List and create users for the current store.
    Only store owners and managers can create users.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StoreUserCreateSerializer
        return StoreUserSerializer
    
    @extend_schema(
        summary="List Store Users",
        description="List all users in the current store",
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/StoreUser'}},
        }
    )
    def get_queryset(self):
        # Get user's store
        store_user = StoreUser.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        
        if not store_user:
            return StoreUser.objects.none()
        
        return StoreUser.objects.filter(
            store=store_user.store,
            is_active=True
        ).select_related('user', 'store', 'assigned_by')
    
    @extend_schema(
        summary="Create Store User",
        description="""
        Create a new user for the current store.
        Only store owners and managers can create users.
        Automatically assigns to the current store.
        """,
        request=StoreUserCreateSerializer,
        responses={
            201: {'$ref': '#/components/schemas/StoreUser'},
            403: {'description': 'Only store owners/managers can create users'}
        },
        examples=[
            OpenApiExample(
                'Create Cashier',
                value={
                    "role": "cashier",
                    "permissions": ["create_orders", "view_orders", "manage_payments"],
                    "user_email": "cashier@restaurant.com",
                    "user_password": "SecurePassword123!",
                    "user_first_name": "Jane",
                    "user_last_name": "Smith",
                    "user_phone": "+1234567891",
                    "user_pin": "654321"
                }
            )
        ]
    )
    def perform_create(self, serializer):
        # Get user's store and check permissions
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can create users')
        
        store = store_user.store
        
        # Check license limits
        if store.license_key:
            current_users = StoreUser.objects.filter(store=store, is_active=True).count()
            if current_users >= store.license_key.max_users:
                raise ValidationError(
                    f'Maximum users ({store.license_key.max_users}) reached for current license'
                )
        
        # Set default permissions based on role
        role = serializer.validated_data.get('role')
        if not serializer.validated_data.get('permissions'):
            serializer.validated_data['permissions'] = DEFAULT_PERMISSIONS.get(role, [])
        
        serializer.save(store=store)

class StoreUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a store user.
    Only store owners/managers can modify users.
    """
    serializer_class = StoreUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'user_id'
    
    @extend_schema(
        summary="Get Store User Details",
        description="Retrieve details of a specific store user",
        responses={
            200: {'$ref': '#/components/schemas/StoreUser'},
            404: {'description': 'User not found'}
        }
    )
    def get_queryset(self):
        # Get user's store
        user_stores = Store.objects.filter(
            store_users__user=self.request.user,
            store_users__is_active=True
        )
        return StoreUser.objects.filter(store__in=user_stores)
    
    @extend_schema(
        summary="Update Store User",
        description="Update store user details. Only store owners/managers allowed.",
        request=StoreUserSerializer
    )
    def perform_update(self, serializer):
        store_user_obj = self.get_object()
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=store_user_obj.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can update users')
        
        serializer.save()
    
    @extend_schema(
        summary="Delete Store User",
        description="Deactivate a store user. Only store owners/managers allowed.",
    )
    def perform_destroy(self, instance):
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=instance.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can delete users')
        
        instance.is_active = False
        instance.save()

# =============== DASHBOARD & UTILITY VIEWS ===============

class DashboardView(APIView):
    """
    Get dashboard statistics for the current store.
    Automatically identifies the store context.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get Store Dashboard",
        description="""
        Get dashboard statistics for the current user's store including:
        - Total branches, users, devices
        - Subscription status
        - License status
        """,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total_branches': {'type': 'integer'},
                    'total_users': {'type': 'integer'},
                    'total_devices': {'type': 'integer'},
                    'subscription_status': {'type': 'object'},
                    'license_status': {'type': 'object'},
                }
            },
            404: {'description': 'Store not found'}
        }
    )
    def get(self, request):
        # Get user's store
        try:
            store_user = StoreUser.objects.get(
                user=request.user,
                is_active=True
            )
            store = store_user.store
        except StoreUser.DoesNotExist:
            return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
        
        stats = {
            'total_branches': store.branches.filter(is_active=True).count(),
            'total_users': store.store_users.filter(is_active=True).count(),
            'total_devices': POSDevice.objects.filter(
                branch__store=store, 
                is_active=True
            ).count(),
            'subscription_status': {
                'is_active': store.is_subscription_active,
                'expires_at': store.subscription_expires_at,
                'plan': store.subscription_plan,
            },
            'license_status': {
                'is_valid': store.is_license_valid,
                'license_key': store.license_key.license_key if store.license_key else None,
                'expires_at': store.license_key.expires_at if store.license_key else None,
            }
        }
        
        return Response(stats)

@extend_schema(
    summary="Check Store Status",
    description="""
    Check current store subscription and license status.
    Includes expiration dates and remaining days.
    """,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'store_code': {'type': 'string'},
                'name': {'type': 'string'},
                'is_active': {'type': 'boolean'},
                'subscription': {'type': 'object'},
                'license': {'type': 'object'},
                'can_login': {'type': 'boolean'},
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_store_status(request):
    # Get user's store
    try:
        store_user = StoreUser.objects.get(
            user=request.user,
            is_active=True
        )
        store = store_user.store
    except StoreUser.DoesNotExist:
        return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
    
    status_info = {
        'store_code': store.store_code,
        'name': store.name,
        'is_active': store.is_active,
        'status': store.status,
        'subscription': {
            'plan': store.subscription_plan,
            'expires_at': store.subscription_expires_at,
            'is_active': store.is_subscription_active,
            'days_remaining': None
        },
        'license': {
            'key': store.license_key.license_key if store.license_key else None,
            'type': store.license_key.license_type if store.license_key else None,
            'expires_at': store.license_key.expires_at if store.license_key else None,
            'is_valid': store.is_license_valid,
            'max_users': store.license_key.max_users if store.license_key else None,
            'max_branches': store.license_key.max_branches if store.license_key else None,
        },
        'can_login': store.can_user_login(store_user.role),
    }
    
    # Calculate days remaining
    if store.subscription_expires_at:
        remaining = store.subscription_expires_at - timezone.now()
        status_info['subscription']['days_remaining'] = max(0, remaining.days)
    
    return Response(status_info)

@extend_schema(
    summary="Update User Permissions",
    description="""
    Update permissions for a specific store user.
    Only store owners can modify user permissions.
    """,
    request={
        'type': 'object',
        'properties': {
            'permissions': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'List of permission codes'
            }
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'user': {'$ref': '#/components/schemas/StoreUser'}
            }
        },
        403: {'description': 'Only store owners can update permissions'}
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_user_permissions(request, user_id):
    # Get store user to update
    try:
        store_user_to_update = StoreUser.objects.get(id=user_id, is_active=True)
    except StoreUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if current user is store owner of the same store
    try:
        current_store_user = StoreUser.objects.get(
            user=request.user,
            store=store_user_to_update.store,
            role='store_owner',
            is_active=True
        )
    except StoreUser.DoesNotExist:
        return Response({
            'error': 'Only store owners can update user permissions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    new_permissions = request.data.get('permissions', [])
    store_user_to_update.permissions = new_permissions
    store_user_to_update.save()
    
    return Response({
        'message': 'Permissions updated successfully',
        'user': StoreUserSerializer(store_user_to_update).data
    })

# =============== PERMISSION VIEWS ===============

class PermissionListView(generics.ListAPIView):
    """
    List all available permissions in the system.
    """
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Permission.objects.filter(is_active=True)
    
    @extend_schema(
        summary="List All Permissions",
        description="Get a list of all available permissions in the system",
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/Permission'}},
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

@extend_schema(
    summary="Get Role Default Permissions",
    description="Get the default permissions assigned to a specific role",
    parameters=[
        OpenApiParameter(
            name='role',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Role name (e.g., cashier, manager, etc.)',
            enum=['store_owner', 'store_manager', 'branch_manager', 'cashier', 'chef', 'waiter']
        )
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'role': {'type': 'string'},
                'permissions': {'type': 'array', 'items': {'type': 'string'}}
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_role_permissions(request, role):
    permissions_list = DEFAULT_PERMISSIONS.get(role, [])
    return Response({
        'role': role,
        'permissions': permissions_list
    })

# =============== POS DEVICE MANAGEMENT VIEWS ===============

class POSDeviceListCreateView(generics.ListCreateAPIView):
    """
    List and create POS devices for branches in the current store.
    """
    serializer_class = POSDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="List POS Devices",
        description="List all POS devices in the current store's branches",
        parameters=[
            OpenApiParameter(
                name='branch_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by specific branch ID (optional)'
            )
        ],
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/POSDevice'}},
        }
    )
    def get_queryset(self):
        # Get user's store
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                is_active=True
            )
            store = store_user.store
        except StoreUser.DoesNotExist:
            return POSDevice.objects.none()
        
        # Filter by branch if specified
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            return POSDevice.objects.filter(
                branch_id=branch_id,
                branch__store=store,
                is_active=True
            )
        
        return POSDevice.objects.filter(
            branch__store=store,
            is_active=True
        )
    
    @extend_schema(
        summary="Create POS Device",
        description="""
        Create a new POS device for a branch.
        Only store owners and managers can create devices.
        """,
        request=POSDeviceSerializer,
        responses={
            201: {'$ref': '#/components/schemas/POSDevice'},
            403: {'description': 'Only store owners/managers can create devices'}
        },
        examples=[
            OpenApiExample(
                'Create Main Counter POS',
                value={
                    "branch": "uuid-of-branch",
                    "device_name": "Main Counter POS",
                    "device_code": "POS001",
                    "device_type": "main_counter",
                    "ip_address": "192.168.1.100",
                    "printer_config": {
                        "receipt_printer": "192.168.1.101",
                        "kitchen_printer": "192.168.1.102"
                    }
                }
            )
        ]
    )
    def perform_create(self, serializer):
        # Check if user can create devices
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can create POS devices')
        
        # Verify branch belongs to user's store
        branch = serializer.validated_data['branch']
        if branch.store != store_user.store:
            raise ValidationError('Branch does not belong to your store')
        
        serializer.save()

class POSDeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a POS device.
    """
    serializer_class = POSDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'device_id'
    
    @extend_schema(
        summary="Get POS Device Details",
        description="Retrieve details of a specific POS device",
        responses={
            200: {'$ref': '#/components/schemas/POSDevice'},
            404: {'description': 'Device not found'}
        }
    )
    def get_queryset(self):
        # Get user's store devices
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                is_active=True
            )
            store = store_user.store
        except StoreUser.DoesNotExist:
            return POSDevice.objects.none()
        
        return POSDevice.objects.filter(branch__store=store)
    
    @extend_schema(
        summary="Update POS Device",
        description="Update POS device details. Only store owners/managers allowed.",
        request=POSDeviceSerializer
    )
    def perform_update(self, serializer):
        device = self.get_object()
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=device.branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can update devices')
        
        serializer.save()
    
    @extend_schema(
        summary="Delete POS Device",
        description="Delete a POS device. Only store owners/managers allowed.",
    )
    def perform_destroy(self, instance):
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=instance.branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can delete devices')
        
        instance.is_active = False
        instance.save()

# =============== BRANCH USER MANAGEMENT VIEWS ===============

class BranchUserListCreateView(generics.ListCreateAPIView):
    """
    List and create users for a specific branch.
    """
    serializer_class = BranchUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="List Branch Users",
        description="List all users assigned to a specific branch",
        parameters=[
            OpenApiParameter(
                name='branch_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Branch ID'
            )
        ],
        responses={
            200: {'type': 'array', 'items': {'$ref': '#/components/schemas/BranchUser'}},
        }
    )
    def get_queryset(self):
        branch_id = self.kwargs['branch_id']
        
        # Verify user has access to this branch's store
        try:
            branch = Branch.objects.get(id=branch_id)
            StoreUser.objects.get(
                user=self.request.user,
                store=branch.store,
                is_active=True
            )
        except (Branch.DoesNotExist, StoreUser.DoesNotExist):
            return BranchUser.objects.none()
        
        return BranchUser.objects.filter(
            branch_id=branch_id,
            is_active=True
        ).select_related('user', 'branch')
    
    @extend_schema(
        summary="Assign User to Branch",
        description="""
        Assign an existing store user to a specific branch.
        Only store owners and managers can assign users to branches.
        """,
        request=BranchUserSerializer,
        responses={
            201: {'$ref': '#/components/schemas/BranchUser'},
            403: {'description': 'Only store owners/managers can assign users to branches'}
        }
    )
    def perform_create(self, serializer):
        branch_id = self.kwargs['branch_id']
        branch = get_object_or_404(Branch, id=branch_id)
        
        # Check permissions
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can assign users to branches')
        
        # Set default permissions based on role
        role = serializer.validated_data.get('role')
        if not serializer.validated_data.get('permissions'):
            serializer.validated_data['permissions'] = DEFAULT_PERMISSIONS.get(role, [])
        
        serializer.save(branch=branch)

class BranchUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a branch user assignment.
    """
    serializer_class = BranchUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'user_id'
    
    @extend_schema(
        summary="Get Branch User Details",
        description="Retrieve details of a specific branch user assignment",
        responses={
            200: {'$ref': '#/components/schemas/BranchUser'},
            404: {'description': 'Branch user not found'}
        }
    )
    def get_queryset(self):
        branch_id = self.kwargs['branch_id']
        
        # Verify access
        try:
            branch = Branch.objects.get(id=branch_id)
            StoreUser.objects.get(
                user=self.request.user,
                store=branch.store,
                is_active=True
            )
        except (Branch.DoesNotExist, StoreUser.DoesNotExist):
            return BranchUser.objects.none()
        
        return BranchUser.objects.filter(branch_id=branch_id)
    
    @extend_schema(
        summary="Update Branch User",
        description="Update branch user assignment. Only store owners/managers allowed.",
        request=BranchUserSerializer
    )
    def perform_update(self, serializer):
        branch_user = self.get_object()
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=branch_user.branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can update branch users')
        
        serializer.save()
    
    @extend_schema(
        summary="Remove User from Branch",
        description="Remove user assignment from branch. Only store owners/managers allowed.",
    )
    def perform_destroy(self, instance):
        try:
            StoreUser.objects.get(
                user=self.request.user,
                store=instance.branch.store,
                role__in=['store_owner', 'store_manager'],
                is_active=True
            )
        except StoreUser.DoesNotExist:
            raise PermissionDenied('Only store owners/managers can remove branch users')
        
        instance.is_active = False
        instance.save()

# =============== PROFILE & USER MANAGEMENT ===============

class MyProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update current user's profile information.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get My Profile",
        description="Get current user's profile information",
        responses={
            200: {'$ref': '#/components/schemas/User'},
        }
    )
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Update My Profile",
        description="Update current user's profile information",
        request=UserSerializer,
        responses={
            200: {'$ref': '#/components/schemas/User'},
        }
    )
    def perform_update(self, serializer):
        # Don't allow changing email or PIN through this endpoint
        if 'email' in serializer.validated_data:
            serializer.validated_data.pop('email')
        if 'pin' in serializer.validated_data:
            serializer.validated_data.pop('pin')
        
        serializer.save()

@extend_schema(
    summary="Change PIN",
    description="Change user's PIN. Requires current PIN for verification.",
    request={
        'type': 'object',
        'properties': {
            'current_pin': {'type': 'string', 'minLength': 6, 'maxLength': 6},
            'new_pin': {'type': 'string', 'minLength': 6, 'maxLength': 6},
        },
        'required': ['current_pin', 'new_pin']
    },
    responses={
        200: {'type': 'object', 'properties': {'message': {'type': 'string'}}},
        400: {'description': 'Invalid current PIN or validation errors'}
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_pin(request):
    current_pin = request.data.get('current_pin')
    new_pin = request.data.get('new_pin')
    
    if not current_pin or not new_pin:
        return Response({
            'error': 'Both current_pin and new_pin are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if request.user.pin != current_pin:
        return Response({
            'error': 'Current PIN is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not new_pin.isdigit() or len(new_pin) != 6:
        return Response({
            'error': 'New PIN must be exactly 6 digits'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    request.user.pin = new_pin
    request.user.save()
    
    return Response({'message': 'PIN changed successfully'})

@extend_schema(
    summary="Get My Store Role",
    description="Get current user's role and permissions in their store",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'store': {'$ref': '#/components/schemas/Store'},
                'role': {'type': 'string'},
                'permissions': {'type': 'array', 'items': {'type': 'string'}},
                'assigned_branches': {'type': 'array', 'items': {'type': 'string'}},
            }
        },
        404: {'description': 'No store assignment found'}
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_store_role(request):
    try:
        store_user = StoreUser.objects.get(
            user=request.user,
            is_active=True
        )
    except StoreUser.DoesNotExist:
        return Response({
            'error': 'No store assignment found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get assigned branches
    branch_assignments = BranchUser.objects.filter(
        user=request.user,
        is_active=True,
        branch__store=store_user.store
    ).select_related('branch')
    
    return Response({
        'store': StoreSerializer(store_user.store).data,
        'role': store_user.role,
        'permissions': store_user.permissions,
        'assigned_branches': [
            {
                'id': str(bu.branch.id),
                'name': bu.branch.name,
                'role': bu.role,
                'permissions': bu.permissions
            }
            for bu in branch_assignments
        ]
    })

# =============== SYSTEM HEALTH & MONITORING ===============

@extend_schema(
    summary="System Health Check",
    description="Check system health and database connectivity",
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string'},
                'timestamp': {'type': 'string'},
                'database': {'type': 'string'},
                'version': {'type': 'string'},
            }
        }
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    try:
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected',
            'version': '1.0.0'
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)