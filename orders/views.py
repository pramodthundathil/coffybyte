from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models
from decimal import Decimal

from .models import Order, OrderItem, Tables, Checkout, SavedItems
from inventory.models import Tax, ModifierOptions, Modifiers
from .serializers import (
    OrderCreateSerializer, OrderReadSerializer, OrderUpdateSerializer,
    CheckoutSerializer, TableSerializer, ItemMoveSerializer, OrderItemCreateSerializer, OrderItemReadSerializer, OrderItemTaxModifierSerializer, BulkOrderItemTaxModifierSerializer
)


class IsStoreUser(permissions.BasePermission):
    """Custom permission to check if user belongs to a store"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.store_memberships.filter(is_active=True).exists()
        )
    
    def has_object_permission(self, request, view, obj):
        user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        return obj.store_id in user_stores


class TableListView(generics.ListAPIView):
    """List all active tables"""
    serializer_class = TableSerializer
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    def get_queryset(self):
        return Tables.objects.filter(status=True)


class OrderCreateView(generics.CreateAPIView):
    """Create a new order"""
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    @swagger_auto_schema(
        operation_description="Create a new order with items",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['order_method', 'items'],
            properties={
                'order_method': openapi.Schema(type=openapi.TYPE_STRING, enum=['Dine In', 'Takeaway', 'Delivery']),
                'table_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Required for Dine In orders'),
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        required=['menu_item_id', 'quantity'],
                        properties={
                            'menu_item_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1),
                            'special_instructions': openapi.Schema(type=openapi.TYPE_STRING),
                            'add_ons': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
                            'taxes': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
                            'is_saved_for_later': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
                        }
                    )
                )
            }
        ),
        responses={
            201: OrderReadSerializer,
            400: 'Bad Request'
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Return the created order with full details
        response_serializer = OrderReadSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """List orders for the user's store"""
    serializer_class = OrderReadSerializer
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    def get_queryset(self):
        user_stores = self.request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        queryset = Order.objects.filter(store_id__in=user_stores).select_related(
            'table', 'user', 'store'
        ).prefetch_related('items__menu_item', 'items__add_ons', 'items__tax')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by order method
        method_filter = self.request.query_params.get('order_method')
        if method_filter:
            queryset = queryset.filter(order_method=method_filter)
        
        # Filter by date
        date_filter = self.request.query_params.get('date')
        if date_filter:
            queryset = queryset.filter(create_date__date=date_filter)
        
        # Filter by checkout status
        checkout_filter = self.request.query_params.get('checkout_status')
        if checkout_filter:
            queryset = queryset.filter(checkout_status=checkout_filter.lower() == 'true')
            
        # Filter orders with saved items
        has_saved_items = self.request.query_params.get('has_saved_items')
        if has_saved_items == 'true':
            queryset = queryset.filter(items__is_saved_for_later=True).distinct()
        
        return queryset.order_by('-create_date')

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by order status", type=openapi.TYPE_STRING),
            openapi.Parameter('order_method', openapi.IN_QUERY, description="Filter by order method", type=openapi.TYPE_STRING),
            openapi.Parameter('date', openapi.IN_QUERY, description="Filter by date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('checkout_status', openapi.IN_QUERY, description="Filter by checkout status", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('has_saved_items', openapi.IN_QUERY, description="Filter orders with saved items", type=openapi.TYPE_BOOLEAN),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class OrderDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a specific order"""
    serializer_class = OrderReadSerializer
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    def get_queryset(self):
        user_stores = self.request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        return Order.objects.filter(store_id__in=user_stores).select_related(
            'table', 'user', 'store'
        ).prefetch_related('items__menu_item', 'items__add_ons', 'items__tax')
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return OrderUpdateSerializer
        return OrderReadSerializer

    @swagger_auto_schema(
        operation_description="Update order status and details",
        request_body=OrderUpdateSerializer,
        responses={200: OrderReadSerializer}
    )
    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return updated order with full details
        response_serializer = OrderReadSerializer(order)
        return Response(response_serializer.data)


@swagger_auto_schema(
    method='post',
    operation_description="Move items between saved and checkout states",
    request_body=ItemMoveSerializer,
    responses={
        200: openapi.Response(description="Items moved successfully"),
        400: openapi.Response(description="Bad Request"),
        404: openapi.Response(description="Order not found"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStoreUser])
def manage_order_items(request, order_id):
    """Move items between saved and checkout states"""
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    
    try:
        order = Order.objects.get(id=order_id, store_id__in=user_stores)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ItemMoveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    item_ids = serializer.validated_data['item_ids']
    action = serializer.validated_data['action']
    
    # Get the items
    items = OrderItem.objects.filter(id__in=item_ids, order=order)
    
    if items.count() != len(item_ids):
        return Response(
            {'error': 'Some items not found or not belong to this order'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with transaction.atomic():
        moved_items = []
        for item in items:
            if action == 'move_to_checkout':
                if item.is_saved_for_later:
                    item.move_to_checkout()
                    moved_items.append(item.id)
            elif action == 'save_for_later':
                if not item.is_saved_for_later:
                    item.save_for_later()
                    moved_items.append(item.id)
        
        # Recalculate order totals
        order.calculate_totals()
        order.save()
        
        # Create saved items log if items were saved
        if action == 'save_for_later' and moved_items:
            total_saved = sum(
                item.get_total_price_with_addons() 
                for item in items.filter(id__in=moved_items)
            )
            SavedItems.objects.create(
                order=order,
                saved_by=request.user,
                items_count=len(moved_items),
                total_saved_amount=total_saved,
                notes=f"Items moved to saved list by {request.user.get_full_name()}"
            )
    
    return Response({
        'message': f'{len(moved_items)} items {action.replace("_", " ")} successfully',
        'moved_items': moved_items,
        'order_totals': {
            'total_before_tax': float(order.total_before_tax),
            'total_tax': float(order.total_tax),
            'total_price': float(order.total_price)
        }
    })


class OrderItemUpdateView(generics.UpdateAPIView):
    """Update order item completion status"""
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    def get_queryset(self):
        user_stores = self.request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        return OrderItem.objects.filter(order__store_id__in=user_stores)
    
    @swagger_auto_schema(
        operation_description="Update order item completion status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'completion_status': openapi.Schema(type=openapi.TYPE_BOOLEAN)
            }
        )
    )
    def patch(self, request, pk):
        order_item = get_object_or_404(self.get_queryset(), pk=pk)
        completion_status = request.data.get('completion_status')
        
        if completion_status is not None:
            order_item.completion_status = completion_status
            order_item.save()
            
            # Check if all checkout items are completed to update order status
            order = order_item.order
            checkout_items = order.items.filter(is_saved_for_later=False)
            all_completed = all(item.completion_status for item in checkout_items)
            
            if all_completed and checkout_items.exists() and order.status != "Order Ready":
                order.status = "Order Ready"
                order.save()
        
        return Response({'message': 'Order item updated successfully'})


@swagger_auto_schema(
    method='post',
    operation_description="Save order ticket (mark as saved without checkout)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'order_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'notes': openapi.Schema(type=openapi.TYPE_STRING)
        },
        required=['order_id']  # only order_id is required
    ),
    responses={
        200: openapi.Response(description="Ticket saved successfully"),
        404: openapi.Response(description="Order not found"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStoreUser])
def save_ticket(request):
    """Save order ticket without checkout"""
    order_id = request.data.get('order_id')
    notes = request.data.get('notes', '')
    
    if not order_id:
        return Response(
            {'error': 'order_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    
    try:
        order = Order.objects.get(id=order_id, store_id__in=user_stores)
        order.take_order = True
        order.save()
        
        # Create saved items log
        saved_items_count = order.items.filter(is_saved_for_later=True).count()
        if saved_items_count > 0:
            total_saved = sum(
                item.get_total_price_with_addons() 
                for item in order.items.filter(is_saved_for_later=True)
            )
            SavedItems.objects.create(
                order=order,
                saved_by=request.user,
                items_count=saved_items_count,
                total_saved_amount=total_saved,
                notes=notes or f"Order ticket saved by {request.user.get_full_name()}"
            )
        
        return Response({
            'message': 'Ticket saved successfully',
            'order_id': order.id,
            'token': order.token,
            'saved_items_count': saved_items_count
        })
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


class CheckoutCreateView(generics.CreateAPIView):
    """Checkout an order"""
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated, IsStoreUser]
    
    @swagger_auto_schema(
        operation_description="Checkout an order and generate receipt",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['order', 'payment_method', 'payment_status'],
            properties={
                'order': openapi.Schema(type=openapi.TYPE_INTEGER),
                'payment_method': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    enum=['Cash', 'Card', 'UPI', 'Tabby', 'Bank Transfer', 'Digital Wallet', 'Split Payment']
                ),
                'payment_status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['Pending', 'Paid', 'Failed', 'Refunded', 'Partial']
                ),
                'payment_reference': openapi.Schema(type=openapi.TYPE_STRING),
                'notes': openapi.Schema(type=openapi.TYPE_STRING),
                'cash_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='For split payments'),
                'card_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='For split payments'),
                'upi_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='For split payments'),
                'other_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='For split payments'),
                'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                'customer_phone': openapi.Schema(type=openapi.TYPE_STRING),
                'delivery_address': openapi.Schema(type=openapi.TYPE_STRING),
                'discount_amount': openapi.Schema(type=openapi.TYPE_NUMBER, default=0),
                'discount_reason': openapi.Schema(type=openapi.TYPE_STRING),
                'service_charge': openapi.Schema(type=openapi.TYPE_NUMBER, default=0),
            }
        ),
        responses={201: CheckoutSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@swagger_auto_schema(
    method='get',
    operation_description="Get receipt data for an order (only checkout items)",
    responses={
        200: openapi.Response(
            description="Receipt data",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'order_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'token': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'store_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'checkout_items': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_OBJECT)  # ✅ must define items
                    ),
                    'saved_items': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(type=openapi.TYPE_OBJECT)  # ✅ must define items
                    ),
                    'subtotal': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'total_tax': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'service_charge': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'discount_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'final_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'payment_method': openapi.Schema(type=openapi.TYPE_STRING),
                    'payment_details': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={   # ✅ explicitly define what’s inside
                            'transaction_id': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    ),
                },
                required=['order_id', 'checkout_items']  # mark only required ones
            )
        ),
        404: openapi.Response(description="Order not found"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreUser])
def get_receipt(request, order_id):
    """Get receipt data for an order (only shows checkout items)"""
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    
    try:
        order = Order.objects.select_related(
            'store', 'table', 'user'
        ).prefetch_related(
            'items__menu_item', 'items__add_ons', 'items__tax'
        ).get(id=order_id, store_id__in=user_stores)
        
        # Get checkout items only
        checkout_items = order.items.filter(is_saved_for_later=False)
        saved_items = order.items.filter(is_saved_for_later=True)
        
        # Prepare receipt items (only checkout items)
        receipt_checkout_items = []
        for item in checkout_items:
            addon_total = sum(addon.price for addon in item.add_ons.all())
            item_total = (item.price + addon_total) * item.quantity
            
            tax_details = []
            for tax in item.tax.all():
                tax_amount = (item_total * tax.tax_percentage) / 100
                tax_details.append({
                    'name': tax.tax_name,
                    'percentage': float(tax.tax_percentage),
                    'amount': float(tax_amount)
                })
            
            receipt_checkout_items.append({
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'unit_price': float(item.price),
                'add_ons': [{'name': addon.name, 'price': float(addon.price)} for addon in item.add_ons.all()],
                'item_total': float(item_total),
                'taxes': tax_details,
                'special_instructions': item.special_instructions
            })
        
        # Prepare saved items info (for reference only, not in receipt)
        receipt_saved_items = []
        for item in saved_items:
            addon_total = sum(addon.price for addon in item.add_ons.all())
            item_total = (item.price + addon_total) * item.quantity
            
            receipt_saved_items.append({
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'unit_price': float(item.price),
                'add_ons': [{'name': addon.name, 'price': float(addon.price)} for addon in item.add_ons.all()],
                'item_total': float(item_total),
                'special_instructions': item.special_instructions,
                'saved_date': item.added_to_order_date
            })
        
        # Get checkout details if exists
        checkout_details = {}
        payment_details = {}
        service_charge = Decimal('0.00')
        discount_amount = Decimal('0.00')
        
        if hasattr(order, 'checkout'):
            checkout = order.checkout
            service_charge = checkout.service_charge
            discount_amount = checkout.discount_amount
            
            payment_details = {
                'method': checkout.payment_method,
                'status': checkout.payment_status,
                'reference': checkout.payment_reference,
            }
            
            if checkout.payment_method == 'Split Payment':
                payment_details['split_details'] = {
                    'cash': float(checkout.cash_amount or 0),
                    'card': float(checkout.card_amount or 0),
                    'upi': float(checkout.upi_amount or 0),
                    'other': float(checkout.other_amount or 0),
                }
        
        final_amount = order.total_price + service_charge - discount_amount
        
        receipt_data = {
            'order_id': order.id,
            'token': order.token,
            'store_name': order.store.name,
            'store_address': order.store.address,
            'table_number': str(order.table) if order.table else order.order_method,
            'order_method': order.order_method,
            'create_date': order.create_date,
            'user_name': order.user.get_full_name(),
            'checkout_items': receipt_checkout_items,
            'saved_items': receipt_saved_items,
            'checkout_items_count': len(receipt_checkout_items),
            'saved_items_count': len(receipt_saved_items),
            'subtotal': float(order.total_before_tax),
            'total_tax': float(order.total_tax),
            'service_charge': float(service_charge),
            'discount_amount': float(discount_amount),
            'final_amount': float(final_amount),
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'payment_details': payment_details,
            'has_saved_items': saved_items.exists(),
        }
        
        return Response(receipt_data)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@swagger_auto_schema(
    method='get',
    operation_description="Get kitchen display orders (orders that are not completed)",
    responses={200: OrderReadSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreUser])
def kitchen_display(request):
    """Get orders for kitchen display (only checkout items)"""
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    
    orders = Order.objects.filter(
        store_id__in=user_stores,
        status__in=['Pending', 'In Progress', 'In Kitchen'],
        take_order=True,
        items__is_saved_for_later=False  # Only show orders with items in checkout
    ).distinct().select_related(
        'table', 'user', 'store'
    ).prefetch_related(
        'items__menu_item', 'items__add_ons', 'items__tax'
    ).order_by('create_date')
    
    serializer = OrderReadSerializer(orders, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Get order statistics for dashboard",
    responses={
        200: openapi.Response(
            description="Order statistics",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'today_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'pending_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'completed_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'today_revenue': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'orders_with_saved_items': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'checkout_only_orders': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreUser])
def order_statistics(request):
    """Get order statistics for dashboard"""
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    today = timezone.now().date()
    
    orders = Order.objects.filter(store_id__in=user_stores)
    
    stats = {
        'today_orders': orders.filter(create_date__date=today).count(),
        'pending_orders': orders.filter(status__in=['Pending', 'In Progress', 'In Kitchen']).count(),
        'completed_orders': orders.filter(status='Completed', create_date__date=today).count(),
        'today_revenue': float(
            orders.filter(
                create_date__date=today, 
                payment_status='Paid'
            ).aggregate(total=models.Sum('total_price'))['total'] or 0
        ),
        'orders_with_saved_items': orders.filter(items__is_saved_for_later=True).distinct().count(),
        'checkout_only_orders': orders.filter(
            items__is_saved_for_later=False,
            checkout_status=True
        ).distinct().count(),
    }
    
    return Response(stats)


@swagger_auto_schema(
    method='get',
    operation_description="Get saved items across all orders",
    responses={200: OrderReadSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStoreUser])
def saved_items_list(request):
    """Get all orders that have saved items"""
    user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
    
    orders = Order.objects.filter(
        store_id__in=user_stores,
        items__is_saved_for_later=True
    ).distinct().select_related(
        'table', 'user', 'store'
    ).prefetch_related(
        'items__menu_item', 'items__add_ons', 'items__tax'
    ).order_by('-create_date')
    
    # Filter by date if provided
    date_filter = request.query_params.get('date')
    if date_filter:
        orders = orders.filter(create_date__date=date_filter)
    
    serializer = OrderReadSerializer(orders, many=True)
    return Response(serializer.data)


# views.py (Add these to your existing order views)

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def add_taxes_modifiers_to_item(request, item_id):
    """Add or update taxes and modifiers for a specific order item"""
    try:
        # Get the order item
        order_item = get_object_or_404(
            OrderItem, 
            id=item_id,
            order__store=request.user_store
        )
        
        # Check if order is already checked out
        if order_item.order.checkout_status and not order_item.is_saved_for_later:
            return Response(
                {'error': 'Cannot modify checked out items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderItemTaxModifierSerializer(
            order_item, 
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                updated_item = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_add_taxes_modifiers(request):
    """Add taxes and modifiers to multiple order items at once"""
    try:
        serializer = BulkOrderItemTaxModifierSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                data = serializer.validated_data
                order_item_ids = data['order_item_ids']
                tax_ids = data.get('tax_ids', [])
                modifier_ids = data.get('modifier_ids', [])
                action = data['action']
                
                # Get order items
                order_items = OrderItem.objects.filter(
                    id__in=order_item_ids,
                    order__store=request.user_store
                )
                
                # Get taxes and modifiers
                taxes = Tax.objects.filter(id__in=tax_ids, store=request.user_store) if tax_ids else []
                modifiers = Modifiers.objects.filter(id__in=modifier_ids, store=request.user_store) if modifier_ids else []
                
                updated_items = []
                
                for item in order_items:
                    # Check if item can be modified
                    if item.order.checkout_status and not item.is_saved_for_later:
                        continue
                    
                    # Handle taxes
                    if tax_ids is not None:
                        if action == 'add':
                            item.tax.add(*taxes)
                        elif action == 'replace':
                            item.tax.set(taxes)
                        elif action == 'remove':
                            item.tax.remove(*taxes)
                    
                    # Handle modifiers
                    if modifier_ids is not None:
                        if action == 'add':
                            item.add_ons.add(*modifiers)
                        elif action == 'replace':
                            item.add_ons.set(modifiers)
                        elif action == 'remove':
                            item.add_ons.remove(*modifiers)
                    
                    updated_items.append(item)
                    
                    # Recalculate order totals
                    item.order.calculate_totals()
                    item.order.save()
                
                # Return updated items
                response_data = OrderItemTaxModifierSerializer(updated_items, many=True).data
                return Response(
                    {'updated_items': response_data},
                    status=status.HTTP_200_OK
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_taxes_modifiers_from_item(request, item_id):
    """Remove specific taxes and modifiers from order item"""
    try:
        order_item = get_object_or_404(
            OrderItem,
            id=item_id,
            order__store=request.user_store
        )
        
        if order_item.order.checkout_status and not order_item.is_saved_for_later:
            return Response(
                {'error': 'Cannot modify checked out items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tax_ids = request.data.get('tax_ids', [])
        modifier_ids = request.data.get('modifier_ids', [])
        
        with transaction.atomic():
            # Remove specific taxes
            if tax_ids:
                taxes_to_remove = Tax.objects.filter(
                    id__in=tax_ids,
                    store=request.user_store
                )
                order_item.tax.remove(*taxes_to_remove)
            
            # Remove specific modifiers
            if modifier_ids:
                modifiers_to_remove = Modifiers.objects.filter(
                    id__in=modifier_ids,
                    store=request.user_store
                )
                order_item.add_ons.remove(*modifiers_to_remove)
            
            # Recalculate order totals
            order_item.order.calculate_totals()
            order_item.order.save()
        
        # Return updated item
        serializer = OrderItemTaxModifierSerializer(order_item)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_all_taxes_modifiers_from_item(request, item_id):
    """Clear all taxes and modifiers from order item"""
    try:
        order_item = get_object_or_404(
            OrderItem,
            id=item_id,
            order__store=request.user_store
        )
        
        if order_item.order.checkout_status and not order_item.is_saved_for_later:
            return Response(
                {'error': 'Cannot modify checked out items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Clear all taxes and modifiers
            order_item.tax.clear()
            order_item.add_ons.clear()
            
            # Recalculate order totals
            order_item.order.calculate_totals()
            order_item.order.save()
        
        return Response(
            {'message': 'All taxes and modifiers cleared successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


