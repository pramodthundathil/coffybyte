 =============== MENU MANAGEMENT ===============

class Category(TimeStampedModel):
    """Menu categories - store specific"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    position = models.IntegerField(default=0)  # For ordering
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'categories'
        unique_together = ['store', 'name']
        ordering = ['position', 'name']

class MenuItem(TimeStampedModel):
    """Menu items - store specific"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Item settings
    sku = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    
    # Tax & Discount
    tax_slab = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_discountable = models.BooleanField(default=True)
    
    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.TimeField(null=True, blank=True)
    available_to = models.TimeField(null=True, blank=True)
    
    # Kitchen settings
    preparation_time = models.IntegerField(default=0)  # in minutes
    kitchen_notes = models.TextField(blank=True)
    
    position = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'menu_items'
        unique_together = ['store', 'name']
        ordering = ['position', 'name']





