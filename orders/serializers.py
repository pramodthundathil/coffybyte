from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from .models import Order, OrderItem, Tables, Checkout, SavedItems
from inventory.models import Menu, Tax, Modifiers
from authentication.models import CustomUser, Store


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tables
        fields = ['id', 'Table_number', 'Number_of_Seats', 'status']
        read_only_fields = ['id', 'date_added']


class OrderItemCreateSerializer(serializers.ModelSerializer):
    menu_item_id = serializers.IntegerField(write_only=True)
    add_ons = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    taxes = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    is_saved_for_later = serializers.BooleanField(default=False, write_only=True)
    
    # Read-only fields for response
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(source='menu_item.price', max_digits=10, decimal_places=2, read_only=True)
    add_ons_details = serializers.SerializerMethodField()
    taxes_details = serializers.SerializerMethodField()
    item_total = serializers.SerializerMethodField()
    item_tax_amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item_id', 'menu_item_name', 'menu_item_price',
            'quantity', 'price', 'special_instructions', 
            'add_ons', 'add_ons_details', 'taxes', 'taxes_details',
            'item_total', 'item_tax_amount', 'completion_status',
            'is_saved_for_later', 'added_to_order_date', 'moved_to_checkout_date'
        ]
        read_only_fields = ['id', 'price', 'completion_status', 'added_to_order_date', 'moved_to_checkout_date']

    def get_add_ons_details(self, obj):
        return [
            {
                'id': addon.id,
                'name': addon.name,
                'price': float(addon.price)
            }
            for addon in obj.add_ons.all()
        ]

    def get_taxes_details(self, obj):
        return [
            {
                'id': tax.id,
                'name': tax.tax_name,
                'percentage': float(tax.tax_percentage)
            }
            for tax in obj.tax.all()
        ]

    def get_item_total(self, obj):
        addon_total = sum(addon.price for addon in obj.add_ons.all())
        return float((obj.price + addon_total) * obj.quantity)

    def get_item_tax_amount(self, obj):
        base_price = obj.price + sum(addon.price for addon in obj.add_ons.all())
        total_tax_percentage = sum(tax.tax_percentage for tax in obj.tax.all())
        tax_amount = (base_price * obj.quantity * total_tax_percentage) / 100
        return float(tax_amount)

    def validate_menu_item_id(self, value):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'store_memberships'):
            raise serializers.ValidationError("User must be associated with a store")
        
        user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        
        try:
            menu_item = Menu.objects.get(id=value, store_id__in=user_stores, status=True)
            return value
        except Menu.DoesNotExist:
            raise serializers.ValidationError("Menu item not found or not accessible")

    def validate_add_ons(self, value):
        if not value:
            return value
        
        request = self.context.get('request')
        user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        
        valid_modifiers = Modifiers.objects.filter(
            id__in=value, 
            store_id__in=user_stores, 
            status=True
        ).count()
        
        if valid_modifiers != len(value):
            raise serializers.ValidationError("Some add-ons are not valid or not accessible")
        
        return value

    def validate_taxes(self, value):
        if not value:
            return value
        
        request = self.context.get('request')
        user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        
        valid_taxes = Tax.objects.filter(
            id__in=value, 
            store_id__in=user_stores, 
            is_active=True
        ).count()
        
        if valid_taxes != len(value):
            raise serializers.ValidationError("Some taxes are not valid or not accessible")
        
        return value


class OrderItemReadSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(source='menu_item.price', max_digits=10, decimal_places=2, read_only=True)
    add_ons_details = serializers.SerializerMethodField()
    taxes_details = serializers.SerializerMethodField()
    item_total = serializers.SerializerMethodField()
    item_tax_amount = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item_name', 'menu_item_price', 'quantity', 
            'price', 'special_instructions', 'add_ons_details', 
            'taxes_details', 'item_total', 'item_tax_amount', 
            'completion_status', 'is_saved_for_later', 'status_display',
            'added_to_order_date', 'moved_to_checkout_date'
        ]

    def get_status_display(self, obj):
        if obj.is_saved_for_later:
            return "Saved for Later"
        elif obj.completion_status:
            return "Completed"
        else:
            return "In Checkout"

    def get_add_ons_details(self, obj):
        return [
            {
                'id': addon.id,
                'name': addon.name,
                'price': float(addon.price)
            }
            for addon in obj.add_ons.all()
        ]

    def get_taxes_details(self, obj):
        return [
            {
                'id': tax.id,
                'name': tax.tax_name,
                'percentage': float(tax.tax_percentage)
            }
            for tax in obj.tax.all()
        ]

    def get_item_total(self, obj):
        addon_total = sum(addon.price for addon in obj.add_ons.all())
        return float((obj.price + addon_total) * obj.quantity)

    def get_item_tax_amount(self, obj):
        base_price = obj.price + sum(addon.price for addon in obj.add_ons.all())
        total_tax_percentage = sum(tax.tax_percentage for tax in obj.tax.all())
        tax_amount = (base_price * obj.quantity * total_tax_percentage) / 100
        return float(tax_amount)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    table_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id', 'token', 'table_id', 'order_method', 'items',
            'status', 'payment_method', 'payment_status', 'is_saved_for_later'
        ]
        read_only_fields = ['id', 'token', 'create_date', 'user', 'store']

    def validate_table_id(self, value):
        if value is not None:
            if not Tables.objects.filter(id=value, status=True).exists():
                raise serializers.ValidationError("Table not found or inactive")
        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        table_id = validated_data.pop('table_id', None)
        
        request = self.context.get('request')
        
        # Get user's active store
        user_store = request.user.store_memberships.filter(is_active=True).first()
        if not user_store:
            raise serializers.ValidationError("User is not associated with any active store")
        
        # Set store and user automatically
        validated_data['store'] = user_store.store
        validated_data['user'] = request.user
        
        # Set table if provided
        if table_id:
            validated_data['table_id'] = table_id

        # Create order
        order = Order.objects.create(**validated_data)
        
        # Calculate totals
        total_before_tax = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        # Create order items
        for item_data in items_data:
            menu_item = Menu.objects.get(id=item_data['menu_item_id'])
            is_saved = item_data.pop('is_saved_for_later', False)
            
            # Create order item
            order_item = OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=menu_item.price,
                special_instructions=item_data.get('special_instructions', ''),
                is_saved_for_later=is_saved
            )
            
            # Add modifiers
            if 'add_ons' in item_data:
                order_item.add_ons.set(item_data['add_ons'])
            
            # Add taxes
            if 'taxes' in item_data:
                order_item.tax.set(item_data['taxes'])
            else:
                # Use menu item's default taxes
                order_item.tax.set(menu_item.taxes.all())
            
            # Calculate totals only for items not saved for later
            if not is_saved:
                addon_total = sum(addon.price for addon in order_item.add_ons.all())
                item_base_price = (order_item.price + addon_total) * order_item.quantity
                
                total_tax_percentage = sum(tax.tax_percentage for tax in order_item.tax.all())
                item_tax_amount = (item_base_price * total_tax_percentage) / 100
                
                total_before_tax += item_base_price
                total_tax += item_tax_amount
        
        # Update order totals
        order.total_before_tax = float(total_before_tax)
        order.total_tax = float(total_tax)
        order.total_price = float(total_before_tax + total_tax)
        order.save()
        
        return order


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    checkout_items = serializers.SerializerMethodField()
    saved_items = serializers.SerializerMethodField()
    table_details = TableSerializer(source='table', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'token', 'table_details', 'order_method', 'store_name',
            'user_name', 'create_date', 'status', 'checkout_status',
            'take_order', 'completion_status', 'total_price', 'total_tax',
            'total_before_tax', 'payment_method', 'payment_status', 'items',
            'checkout_items', 'saved_items', 'is_saved_for_later'
        ]

    def get_checkout_items(self, obj):
        """Get items that are ready for checkout"""
        checkout_items = obj.items.filter(is_saved_for_later=False)
        return OrderItemReadSerializer(checkout_items, many=True).data

    def get_saved_items(self, obj):
        """Get items that are saved for later"""
        saved_items = obj.items.filter(is_saved_for_later=True)
        return OrderItemReadSerializer(saved_items, many=True).data


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'status', 'checkout_status', 'take_order', 'completion_status',
            'payment_method', 'payment_status'
        ]


class ItemMoveSerializer(serializers.Serializer):
    """Serializer for moving items between saved and checkout"""
    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(
        choices=[('move_to_checkout', 'Move to Checkout'), ('save_for_later', 'Save for Later')]
    )


class CheckoutSerializer(serializers.ModelSerializer):
    order_details = OrderReadSerializer(source='order', read_only=True)
    checkout_items = serializers.SerializerMethodField(read_only=True)
    final_amount = serializers.SerializerMethodField(read_only=True)
    split_payment_valid = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Checkout
        fields = [
            'id', 'order', 'total_price', 'tax_amount', 'payment_method',
            'payment_status', 'datetime', 'order_details', 'checkout_items',
            'payment_reference', 'notes', 'cash_amount', 'card_amount',
            'upi_amount', 'other_amount', 'customer_name', 'customer_phone',
            'delivery_address', 'discount_amount', 'discount_reason',
            'service_charge', 'final_amount', 'split_payment_valid'
        ]
        read_only_fields = ['id', 'datetime']

    def get_checkout_items(self, obj):
        """Get only items that are in checkout (not saved for later)"""
        checkout_items = obj.get_checkout_items()
        return OrderItemReadSerializer(checkout_items, many=True).data

    def get_final_amount(self, obj):
        return float(obj.calculate_final_amount())

    def get_split_payment_valid(self, obj):
        return obj.validate_split_payment()

    def validate_order(self, value):
        request = self.context.get('request')
        user_stores = request.user.store_memberships.filter(is_active=True).values_list('store_id', flat=True)
        
        if value.store_id not in user_stores:
            raise serializers.ValidationError("Order not found or not accessible")
        
        if hasattr(value, 'checkout'):
            raise serializers.ValidationError("Order is already checked out")
        
        # Check if order has items ready for checkout
        checkout_items = value.items.filter(is_saved_for_later=False)
        if not checkout_items.exists():
            raise serializers.ValidationError("No items available for checkout. Move items from saved list first.")
        
        return value

    def validate(self, data):
        # Validate split payment if applicable
        if data.get('payment_method') == 'Split Payment':
            total_paid = (
                (data.get('cash_amount') or Decimal('0.00')) +
                (data.get('card_amount') or Decimal('0.00')) +
                (data.get('upi_amount') or Decimal('0.00')) +
                (data.get('other_amount') or Decimal('0.00'))
            )
            
            expected_total = data.get('total_price', Decimal('0.00'))
            service_charge = data.get('service_charge', Decimal('0.00'))
            discount = data.get('discount_amount', Decimal('0.00'))
            final_total = expected_total + service_charge - discount
            
            if abs(total_paid - final_total) > Decimal('0.01'):
                raise serializers.ValidationError(
                    f"Split payment amounts ({total_paid}) don't match final total ({final_total})"
                )
        
        return data

    def create(self, validated_data):
        order = validated_data['order']
        
        # Recalculate order totals based only on checkout items
        order.calculate_totals()
        order.save()
        
        # Update order checkout status
        order.checkout_status = True
        order.payment_method = validated_data['payment_method']
        order.payment_status = validated_data['payment_status']
        order.save()
        
        # Create checkout record
        validated_data['total_price'] = order.total_price
        validated_data['tax_amount'] = order.total_tax
        
        return Checkout.objects.create(**validated_data)
    



# serializers.py (Add these to your existing order serializers)

from rest_framework import serializers
from .models import OrderItem
from inventory.models import Tax, Modifiers
from inventory.serializers import TaxSerializer, ModifiersSerializer


class OrderItemTaxModifierSerializer(serializers.ModelSerializer):
    """Serializer for adding/updating taxes and modifiers to order items"""
    tax_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    modifier_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        allow_empty=True
    )
    
    # Read-only fields for response
    tax = TaxSerializer(many=True, read_only=True)
    add_ons = ModifiersSerializer(many=True, read_only=True)
    total_price_with_addons = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'tax_ids', 'modifier_ids', 'tax', 'add_ons',
            'total_price_with_addons', 'tax_amount', 'final_price'
        ]
    
    def get_total_price_with_addons(self, obj):
        return obj.get_total_price_with_addons()
    
    def get_tax_amount(self, obj):
        return obj.get_tax_amount()
    
    def get_final_price(self, obj):
        return obj.get_total_price_with_addons() + obj.get_tax_amount()
    
    def validate_tax_ids(self, value):
        """Validate tax IDs exist and belong to the same store"""
        if not value:
            return value
        
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            taxes = Tax.objects.filter(id__in=value, store=store, is_active=True)
            if len(taxes) != len(value):
                raise serializers.ValidationError("Some tax IDs are invalid or don't belong to your store.")
        return value
    
    def validate_modifier_ids(self, value):
        """Validate modifier IDs exist and belong to the same store"""
        if not value:
            return value
        
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            modifiers = Modifiers.objects.filter(id__in=value, store=store, status=True)
            if len(modifiers) != len(value):
                raise serializers.ValidationError("Some modifier IDs are invalid or don't belong to your store.")
        return value
    
    def update(self, instance, validated_data):
        tax_ids = validated_data.get('tax_ids')
        modifier_ids = validated_data.get('modifier_ids')
        
        # Update taxes if provided
        if tax_ids is not None:
            if tax_ids:
                taxes = Tax.objects.filter(id__in=tax_ids)
                instance.tax.set(taxes)
            else:
                instance.tax.clear()
        
        # Update modifiers if provided
        if modifier_ids is not None:
            if modifier_ids:
                modifiers = Modifiers.objects.filter(id__in=modifier_ids)
                instance.add_ons.set(modifiers)
            else:
                instance.add_ons.clear()
        
        instance.save()
        
        # Recalculate order totals
        instance.order.calculate_totals()
        instance.order.save()
        
        return instance


class BulkOrderItemTaxModifierSerializer(serializers.Serializer):
    """Serializer for adding taxes and modifiers to multiple order items"""
    order_item_ids = serializers.ListField(child=serializers.IntegerField())
    tax_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False,
        allow_empty=True
    )
    modifier_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False,
        allow_empty=True
    )
    action = serializers.ChoiceField(
        choices=['add', 'replace', 'remove'],
        default='add'
    )
    
    def validate_order_item_ids(self, value):
        """Validate order item IDs exist"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            items = OrderItem.objects.filter(
                id__in=value,
                order__store=store
            )
            if len(items) != len(value):
                raise serializers.ValidationError("Some order item IDs are invalid.")
        return value




# Usage Examples:

"""
1. Add taxes and modifiers to an order item:
PUT /order-items/123/taxes-modifiers/
{
    "tax_ids": [1, 2],
    "modifier_ids": [3, 4, 5]
}

2. Replace existing taxes and modifiers:
PUT /order-items/123/taxes-modifiers/
{
    "tax_ids": [1],
    "modifier_ids": [3]
}

3. Remove specific taxes and modifiers:
DELETE /order-items/123/taxes-modifiers/remove/
{
    "tax_ids": [1],
    "modifier_ids": [3]
}

4. Clear all taxes and modifiers:
DELETE /order-items/123/taxes-modifiers/clear/

5. Bulk add to multiple items:
POST /order-items/bulk-taxes-modifiers/
{
    "order_item_ids": [123, 124, 125],
    "tax_ids": [1, 2],
    "modifier_ids": [3, 4],
    "action": "add"  # or "replace" or "remove"
}
"""