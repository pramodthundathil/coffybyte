from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models

from authentication.models import Store, StoreUser
from authentication.permissions import IsStoreOwner
from .models import Tax, Modifiers, ModifierOptions, FoodCategory, Menu
from .serializers import (
    TaxSerializer, ModifiersSerializer, ModifiersCreateSerializer,
    ModifierOptionsSerializer, FoodCategorySerializer, MenuListSerializer,
    MenuDetailSerializer, MenuCreateUpdateSerializer
)


class StoreContextMixin:
    """Mixin to automatically get user's store and filter queryset"""
    
    def get_user_store(self):
        """Get the user's store from StoreUser relationship"""
        if not hasattr(self.request, 'user_store'):
            try:
                # Get the user's active store membership
                store_user = StoreUser.objects.select_related('store').get(
                    user=self.request.user,
                    is_active=True,
                    store__is_active=True
                )
                self.request.user_store = store_user.store
                self.request.user_store_role = store_user.role
            except StoreUser.DoesNotExist:
                # Instead of raising Response, use a proper exception
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You are not associated with any active store.")
        return self.request.user_store
    
    def get_queryset(self):
        """Filter queryset by user's store"""
        store = self.get_user_store()
        return super().get_queryset().filter(store=store)

    def perform_create(self, serializer):
        """Add user's store to the created object"""
        store = self.get_user_store()
        serializer.save(store=store)

    def get_serializer_context(self):
        """Add request context to serializers"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# Tax Views
class TaxListCreateView(StoreContextMixin, generics.ListCreateAPIView):
    """
    get: List all taxes for user's store
    post: Create a new tax (store owners only)
    """
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['tax_name']
    ordering_fields = ['tax_name', 'tax_percentage', 'created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStoreOwner()]
        return [IsAuthenticated()]


class TaxRetrieveUpdateDestroyView(StoreContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    get: Get tax details (authenticated users)
    put/patch: Update tax (store owners only)  
    delete: Delete tax (store owners only)
    """
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsStoreOwner()]
        return [IsAuthenticated()]


# Modifier Views
class ModifierListCreateView(StoreContextMixin, generics.ListCreateAPIView):
    """
    get: List all modifiers for user's store
    post: Create a new modifier with options (store owners only)
    """
    queryset = Modifiers.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ModifiersCreateSerializer
        return ModifiersSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStoreOwner()]
        return [IsAuthenticated()]


class ModifierRetrieveUpdateDestroyView(StoreContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    get: Get modifier details with options (authenticated users)
    put/patch: Update modifier and options (store owners only)
    delete: Delete modifier (store owners only)
    """
    queryset = Modifiers.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ModifiersCreateSerializer
        return ModifiersSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsStoreOwner()]
        return [IsAuthenticated()]


# Modifier Options Views
class ModifierOptionsListCreateView(generics.ListCreateAPIView):
    """
    get: List all options for a specific modifier
    post: Create a new option for a modifier (store owners only)
    """
    serializer_class = ModifierOptionsSerializer

    def get_queryset(self):
        modifier_id = self.kwargs.get('modifier_id')
        # Ensure modifier belongs to user's store
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                is_active=True,
                store__is_active=True
            )
            modifier = get_object_or_404(
                Modifiers, 
                id=modifier_id, 
                store=store_user.store
            )
            return ModifierOptions.objects.filter(modifier=modifier)
        except StoreUser.DoesNotExist:
            return ModifierOptions.objects.none()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStoreOwner()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        modifier_id = self.kwargs.get('modifier_id')
        # Ensure modifier belongs to user's store
        store_user = StoreUser.objects.get(
            user=self.request.user,
            is_active=True,
            store__is_active=True
        )
        modifier = get_object_or_404(
            Modifiers, 
            id=modifier_id, 
            store=store_user.store
        )
        serializer.save(modifier=modifier)


class ModifierOptionsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    get: Get option details (authenticated users)
    put/patch: Update option (store owners only)
    delete: Delete option (store owners only)
    """
    serializer_class = ModifierOptionsSerializer

    def get_queryset(self):
        # Ensure option's modifier belongs to user's store
        try:
            store_user = StoreUser.objects.get(
                user=self.request.user,
                is_active=True,
                store__is_active=True
            )
            return ModifierOptions.objects.filter(modifier__store=store_user.store)
        except StoreUser.DoesNotExist:
            return ModifierOptions.objects.none()

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsStoreOwner()]
        return [IsAuthenticated()]


# Food Category Views
class FoodCategoryListCreateView(StoreContextMixin, generics.ListCreateAPIView):
    """
    get: List all food categories for user's store
    post: Create a new food category (store owners only)
    """
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['active']
    search_fields = ['name']
    ordering_fields = ['name', 'date_added']
    ordering = ['-date_added']
     

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStoreOwner()]
        return [IsAuthenticated()]


class FoodCategoryRetrieveUpdateDestroyView(StoreContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    get: Get category details (authenticated users)
    put/patch: Update category (store owners only)
    delete: Delete category (store owners only)
    """
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategorySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsStoreOwner()]
        return [IsAuthenticated()]


# Menu Views
class MenuListCreateView(StoreContextMixin, generics.ListCreateAPIView):
    """
    get: List all menu items for user's store
    post: Create a new menu item (store owners only)
    """
    queryset = Menu.objects.select_related('category').prefetch_related('taxes', 'modifiers')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'diet', 'portion', 'category', 'stock_track']
    search_fields = ['name', 'description', 'code', 'barcode']
    ordering_fields = ['name', 'price', 'create_date']
    ordering = ['-create_date']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MenuCreateUpdateSerializer
        return MenuListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsStoreOwner()]
        return [IsAuthenticated()]


class MenuRetrieveUpdateDestroyView(StoreContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    get: Get menu item details (authenticated users)
    put/patch: Update menu item (store owners only)
    delete: Delete menu item (store owners only)
    """
    queryset = Menu.objects.select_related('category').prefetch_related('taxes', 'modifiers')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MenuCreateUpdateSerializer
        return MenuDetailSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsStoreOwner()]
        return [IsAuthenticated()]


# Additional utility views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def menu_by_category(request, category_id):
    """Get all menu items for a specific category in user's store"""
    try:
        # Get user's store
        store_user = StoreUser.objects.select_related('store').get(
            user=request.user,
            is_active=True,
            store__is_active=True
        )
        store = store_user.store
        
        # Get category that belongs to user's store
        category = get_object_or_404(FoodCategory, id=category_id, store=store)
        
        menu_items = Menu.objects.filter(
            category=category,
            status=True
        ).select_related('category').prefetch_related('taxes', 'modifiers')
        
        serializer = MenuListSerializer(menu_items, many=True)
        return Response({
            'category': FoodCategorySerializer(category).data,
            'menu_items': serializer.data
        })
        
    except StoreUser.DoesNotExist:
        return Response(
            {"detail": "You are not associated with any active store."},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['POST'])
@permission_classes([IsStoreOwner])
def bulk_update_menu_status(request):
    """Bulk update menu item status for user's store"""
    try:
        # Get user's store
        store_user = StoreUser.objects.select_related('store').get(
            user=request.user,
            is_active=True,
            store__is_active=True
        )
        store = store_user.store
        
        menu_ids = request.data.get('menu_ids', [])
        new_status = request.data.get('status', True)
        
        if not menu_ids:
            return Response(
                {"detail": "menu_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = Menu.objects.filter(
            id__in=menu_ids,
            store=store
        ).update(status=new_status)
        
        return Response({
            "detail": f"Updated {updated_count} menu items",
            "updated_count": updated_count
        })
        
    except StoreUser.DoesNotExist:
        return Response(
            {"detail": "You are not associated with any active store."},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def menu_dashboard(request):
    """Get menu dashboard data for user's store"""
    try:
        # Get user's store
        store_user = StoreUser.objects.select_related('store').get(
            user=request.user,
            is_active=True,
            store__is_active=True
        )
        store = store_user.store
        
        # Get dashboard statistics
        total_menu_items = Menu.objects.filter(store=store).count()
        active_menu_items = Menu.objects.filter(store=store, status=True).count()
        total_categories = FoodCategory.objects.filter(store=store, active=True).count()
        
        # Count low stock items
        low_stock_items = Menu.objects.filter(
            store=store,
            stock_track=True,
            stock__lte=models.F('stock_alert')
        ).count()
        
        # Additional stats
        total_taxes = Tax.objects.filter(store=store, is_active=True).count()
        total_modifiers = Modifiers.objects.filter(store=store, status=True).count()
        
        return Response({
            'store_info': {
                'name': store.name,
                'store_code': store.store_code,
                'business_type': store.business_type
            },
            'menu_stats': {
                'total_menu_items': total_menu_items,
                'active_menu_items': active_menu_items,
                'inactive_menu_items': total_menu_items - active_menu_items,
                'total_categories': total_categories,
                'low_stock_items': low_stock_items,
                'total_taxes': total_taxes,
                'total_modifiers': total_modifiers
            }
        })
        
    except StoreUser.DoesNotExist:
        return Response(
            {"detail": "You are not associated with any active store."},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_menu_items(request):
    """Search menu items across categories in user's store"""
    try:
        # Get user's store
        store_user = StoreUser.objects.select_related('store').get(
            user=request.user,
            is_active=True,
            store__is_active=True
        )
        store = store_user.store
        
        query = request.GET.get('q', '')
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search across menu items
        menu_items = Menu.objects.filter(
            store=store,
            status=True
        ).filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(code__icontains=query) |
            models.Q(barcode__icontains=query)
        ).select_related('category').prefetch_related('taxes', 'modifiers')[:20]  # Limit results
        
        serializer = MenuListSerializer(menu_items, many=True)
        return Response({
            'query': query,
            'results_count': len(menu_items),
            'menu_items': serializer.data
        })
        
    except StoreUser.DoesNotExist:
        return Response(
            {"detail": "You are not associated with any active store."},
            status=status.HTTP_403_FORBIDDEN
        )


@api_view(['POST'])
@permission_classes([IsStoreOwner])
def duplicate_menu_item(request, menu_id):
    """Duplicate a menu item with modifications"""
    try:
        # Get user's store
        store_user = StoreUser.objects.select_related('store').get(
            user=request.user,
            is_active=True,
            store__is_active=True
        )
        store = store_user.store
        
        # Get original menu item
        original_item = get_object_or_404(
            Menu.objects.prefetch_related('taxes', 'modifiers'),
            id=menu_id,
            store=store
        )
        
        # Get new name and portion from request
        new_name = request.data.get('name', f"{original_item.name} - Copy")
        new_portion = request.data.get('portion', original_item.portion)
        
        # Check if combination already exists
        if Menu.objects.filter(store=store, name=new_name, portion=new_portion).exists():
            return Response(
                {"detail": "Menu item with this name and portion already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create duplicate
        new_item = Menu.objects.create(
            store=store,
            category=original_item.category,
            name=new_name,
            image=original_item.image,
            color=original_item.color,
            portion=new_portion,
            diet=original_item.diet,
            price=original_item.price,
            status=True,  # Start as active
            stock_track=original_item.stock_track,
            stock=original_item.stock,
            stock_alert=original_item.stock_alert,
            description=original_item.description,
            code=None,  # Clear code to avoid uniqueness issues
            barcode=None  # Clear barcode
        )
        
        # Copy many-to-many relationships
        new_item.taxes.set(original_item.taxes.all())
        new_item.modifiers.set(original_item.modifiers.all())
        
        # Calculate tax details
        new_item.calculate_tax_details()
        new_item.save()
        
        serializer = MenuDetailSerializer(new_item)
        return Response({
            "detail": "Menu item duplicated successfully",
            "new_item": serializer.data
        })
        
    except StoreUser.DoesNotExist:
        return Response(
            {"detail": "You are not associated with any active store."},
            status=status.HTTP_403_FORBIDDEN
        )