from rest_framework import serializers
from .models import Tax, Modifiers, ModifierOptions, FoodCategory, Menu
from authentication.models import StoreUser


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ['id', 'tax_name', 'tax_percentage', 'is_active', 'created_at']
        read_only_fields = ['created_at']

    def validate_tax_name(self, value):
        """Validate unique tax name within store"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            # Check for duplicate tax name in the same store
            queryset = Tax.objects.filter(store=store, tax_name=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError("Tax with this name already exists in your store.")
        return value


class ModifierOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOptions
        fields = ['id', 'name', 'price']


class ModifiersSerializer(serializers.ModelSerializer):
    options = ModifierOptionsSerializer(many=True, read_only=True)
    
    class Meta:
        model = Modifiers
        fields = ['id', 'name', 'price', 'status', 'created_at', 'options']
        read_only_fields = ['created_at']

    def validate_name(self, value):
        """Validate unique modifier name within store"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            queryset = Modifiers.objects.filter(store=store, name=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError("Modifier with this name already exists in your store.")
        return value


class ModifiersCreateSerializer(serializers.ModelSerializer):
    options = ModifierOptionsSerializer(many=True, required=False)
    
    class Meta:
        model = Modifiers
        fields = ['id', 'name', 'price', 'status', 'created_at', 'options']
        read_only_fields = ['created_at']

    def validate_name(self, value):
        """Validate unique modifier name within store"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            queryset = Modifiers.objects.filter(store=store, name=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError("Modifier with this name already exists in your store.")
        return value

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        
        # Get store from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            validated_data['store'] = request.user_store
        
        modifier = Modifiers.objects.create(**validated_data)
        
        for option_data in options_data:
            ModifierOptions.objects.create(modifier=modifier, **option_data)
        
        return modifier

    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)
        
        # Update modifier fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update options if provided
        if options_data is not None:
            # Clear existing options
            instance.options.all().delete()
            # Create new options
            for option_data in options_data:
                ModifierOptions.objects.create(modifier=instance, **option_data)
        
        return instance


class FoodCategorySerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'image', 'date_added', 'active', 'items_count']
        read_only_fields = ['date_added', 'items_count']

    def get_items_count(self, obj):
        return obj.items.filter(status=True).count()

    def validate_name(self, value):
        """Validate unique category name within store"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            queryset = FoodCategory.objects.filter(store=store, name=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError("Category with this name already exists in your store.")
        return value

    def create(self, validated_data):
        # Get store from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            validated_data['store'] = request.user_store
        return super().create(validated_data)


class MenuListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    taxes_detail = TaxSerializer(source='taxes', many=True, read_only=True)
    modifiers_detail = ModifiersSerializer(source='modifiers', many=True, read_only=True)
    
    class Meta:
        model = Menu
        fields = [
            'id', 'name', 'image', 'color', 'portion', 'diet', 'price', 
            'status', 'description', 'category_name', 'price_before_tax', 
            'total_tax_amount', 'taxes_detail', 'modifiers_detail', 'stock',
            'stock_track', 'code', 'barcode'
        ]


class MenuDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    taxes_detail = TaxSerializer(source='taxes', many=True, read_only=True)
    modifiers_detail = ModifiersSerializer(source='modifiers', many=True, read_only=True)
    
    class Meta:
        model = Menu
        fields = '__all__'
        read_only_fields = ['create_date', 'price_before_tax', 'total_tax_amount', 'store']


class MenuCreateUpdateSerializer(serializers.ModelSerializer):
    taxes = serializers.PrimaryKeyRelatedField(
        queryset=Tax.objects.none(), 
        many=True, 
        required=False,
        allow_empty=True
    )
    modifiers = serializers.PrimaryKeyRelatedField(
        queryset=Modifiers.objects.none(), 
        many=True, 
        required=False,
        allow_empty=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=FoodCategory.objects.none(),
        required=True
    )
    
    class Meta:
        model = Menu
        fields = [
            'category', 'name', 'image', 'color', 'portion', 'diet',
            'price', 'status', 'stock_track', 'stock', 'stock_alert', 
            'description', 'code', 'barcode', 'taxes', 'modifiers'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            # Debug: Print store and available modifiers
            print(f"Current store: {store}")
            print(f"Available modifiers: {list(Modifiers.objects.filter(store=store, status=True).values('id', 'name'))}")
            
            # Filter querysets based on current user's store
            self.fields['taxes'].queryset = Tax.objects.filter(store=store, is_active=True)
            self.fields['modifiers'].queryset = Modifiers.objects.filter(store=store, status=True)
            self.fields['category'].queryset = FoodCategory.objects.filter(store=store, active=True)
        else:
            print("No store found in request context")

    def validate_modifiers(self, value):
        """Custom validation for modifiers"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            for modifier in value:
                if modifier.store != store:
                    raise serializers.ValidationError(f"Modifier '{modifier.name}' does not belong to your store.")
                if not modifier.status:
                    raise serializers.ValidationError(f"Modifier '{modifier.name}' is inactive.")
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            store = request.user_store
            name = attrs.get('name')
            portion = attrs.get('portion')
            
            # Check for duplicate menu item (same name and portion in same store)
            queryset = Menu.objects.filter(store=store, name=name, portion=portion)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError({
                    'name': "Menu item with this name and portion already exists in your store."
                })
            
            # Validate that category belongs to the same store
            category = attrs.get('category')
            if category and category.store != store:
                raise serializers.ValidationError({
                    'category': "Category must belong to your store."
                })
            
            # Validate that taxes belong to the same store
            taxes = attrs.get('taxes', [])
            for tax in taxes:
                if tax.store != store:
                    raise serializers.ValidationError({
                        'taxes': "All taxes must belong to your store."
                    })
        
        return attrs

    def create(self, validated_data):
        taxes_data = validated_data.pop('taxes', [])
        modifiers_data = validated_data.pop('modifiers', [])
        
        # Get store from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user_store'):
            validated_data['store'] = request.user_store
        
        menu_item = Menu.objects.create(**validated_data)
        
        # Set many-to-many relationships
        if taxes_data:
            menu_item.taxes.set(taxes_data)
        if modifiers_data:
            menu_item.modifiers.set(modifiers_data)
        
        # Calculate tax details
        menu_item.calculate_tax_details()
        menu_item.save()
        
        return menu_item

    def update(self, instance, validated_data):
        taxes_data = validated_data.pop('taxes', None)
        modifiers_data = validated_data.pop('modifiers', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update many-to-many relationships
        if taxes_data is not None:
            instance.taxes.set(taxes_data)
        if modifiers_data is not None:
            instance.modifiers.set(modifiers_data)
        
        # Recalculate tax details
        instance.calculate_tax_details()
        instance.save()
        
        return instance