from django.db import models
from inventory.models import Menu, Tax, FoodCategory, Modifiers
from authentication.models import CustomUser, Store
from datetime import datetime as dt
from decimal import Decimal

# Create your models here.

class Tables(models.Model):
    Table_number = models.IntegerField()
    Number_of_Seats = models.IntegerField()
    date_added = models.DateField(auto_now_add=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        if self.Table_number == 100:
            return "Takeaway"
        elif self.Table_number == 101:
            return "Home Delivery"
        return f"Table: {self.Table_number}"

    class Meta:
        verbose_name_plural = "Tables"
        ordering = ['Table_number']


class Order(models.Model):
    token = models.IntegerField(default=0)
    table = models.ForeignKey(Tables, on_delete=models.CASCADE, null=True, blank=True)

    ORDER_METHOD_CHOICES = (
        ("Dine In", "Dine In"),
        ("Takeaway", "Takeaway"),
        ("Delivery", "Delivery"),
    )
    order_method = models.CharField(max_length=20, choices=ORDER_METHOD_CHOICES)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='created_orders')
    create_date = models.DateTimeField(auto_now_add=True)
    
    status_options = (
        ("Pending", "Pending"), 
        ("In Kitchen", "In Kitchen"),
        ("In Progress", "In Progress"),
        ("Order Ready", "Order Ready"), 
        ("Completed", "Completed")
    )
    status = models.CharField(max_length=20, choices=status_options, default="Pending")
    checkout_status = models.BooleanField(default=False)
    take_order = models.BooleanField(default=False)
    completion_status = models.BooleanField(default=False)
    
    # New field to distinguish between saved and checked out items
    is_saved_for_later = models.BooleanField(default=False)

    # Pricing fields
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_before_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Payment fields - Updated with more options
    PAYMENT_METHOD_CHOICES = (
        ("Cash", "Cash"),
        ("Card", "Card"),
        ("UPI", "UPI"),
        ("Tabby", "Tabby"),
        ("Bank Transfer", "Bank Transfer"),
        ("Digital Wallet", "Digital Wallet"),
        ("Split Payment", "Split Payment"),
        ("Pending", "Pending")
    )
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default="Pending")
    payment_status = models.CharField(
        max_length=20, 
        choices=(("Pending", "Pending"), ("Paid", "Paid"), ("Partial", "Partial")),
        default="Pending"
    )

    def save(self, *args, **kwargs):
        if not self.pk:
            today = dt.now().date()
            last_token = Order.objects.filter(
                create_date__date=today,
                store=self.store
            ).aggregate(max_token=models.Max('token'))['max_token'] or 0
            self.token = last_token + 1
            print(f"Generated token: {self.token}")

        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Recalculate order totals based on items"""
        total_before_tax = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        # Only calculate for items that are not saved for later (i.e., items in checkout)
        items_to_calculate = self.items.filter(is_saved_for_later=False)
        
        for item in items_to_calculate:
            # Base item price + addons
            addon_total = sum(Decimal(str(addon.price)) for addon in item.add_ons.all())
            item_base_total = (Decimal(str(item.price)) + addon_total) * item.quantity
            
            # Calculate tax for this item
            item_tax_total = Decimal('0.00')
            for tax in item.tax.all():
                tax_amount = (item_base_total * tax.tax_percentage) / 100
                item_tax_total += tax_amount
            
            total_before_tax += item_base_total
            total_tax += item_tax_total
        
        self.total_before_tax = total_before_tax
        self.total_tax = total_tax
        self.total_price = total_before_tax + total_tax
        
    def __str__(self):
        return f"#{self.id} - Token: {self.token} - {self.table if self.table else self.order_method}"

    class Meta:
        ordering = ['-create_date']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu_item = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.CharField(max_length=500, null=True, blank=True)
    add_ons = models.ManyToManyField(Modifiers, blank=True, related_name='order_items')
    completion_status = models.BooleanField(default=False) 
    tax = models.ManyToManyField(Tax, blank=True, related_name='order_items')
    
    # New field to track if item is saved for later or ready for checkout
    is_saved_for_later = models.BooleanField(default=False)
    
    # Timestamps for tracking
    added_to_order_date = models.DateTimeField(auto_now_add=True)
    moved_to_checkout_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Round price to 2 decimal places
        self.price = round(self.price, 2)
        super().save(*args, **kwargs)

    def get_total_price_with_addons(self):
        """Get total price including addons"""
        addon_total = sum(addon.price for addon in self.add_ons.all())
        return (self.price + addon_total) * self.quantity
    
    def get_tax_amount(self):
        """Calculate total tax amount for this item"""
        base_price = self.get_total_price_with_addons()
        total_tax_percentage = sum(tax.tax_percentage for tax in self.tax.all())
        return (base_price * total_tax_percentage) / 100

    def move_to_checkout(self):
        """Move item from saved to checkout"""
        from django.utils import timezone
        self.is_saved_for_later = False
        self.moved_to_checkout_date = timezone.now()
        self.save()

    def save_for_later(self):
        """Save item for later (remove from checkout)"""
        self.is_saved_for_later = True
        self.moved_to_checkout_date = None
        self.save()

    def __str__(self):
        status = " (Saved)" if self.is_saved_for_later else " (In Checkout)"
        return f"{self.quantity} x {self.menu_item.name}{status}"

    class Meta:
        ordering = ['id']


class Checkout(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='checkout')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Enhanced payment method choices
    PAYMENT_METHOD_CHOICES = (
        ("Cash", "Cash"),
        ("Card", "Card"), 
        ("UPI", "UPI"),
        ("Tabby", "Tabby"),
        ("Bank Transfer", "Bank Transfer"),
        ("Digital Wallet", "Digital Wallet"),
        ("Split Payment", "Split Payment")
    )
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    
    PAYMENT_STATUS_CHOICES = (
        ("Pending", "Pending"), 
        ("Paid", "Paid"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
        ("Partial", "Partial")
    )
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    datetime = models.DateTimeField(auto_now_add=True)
    
    # Additional checkout fields
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Split payment support
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    upi_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Customer details for delivery
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    delivery_address = models.TextField(null=True, blank=True)
    
    # Discount and offers
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_reason = models.CharField(max_length=200, null=True, blank=True)
    
    # Service charge
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    def get_checkout_items(self):
        """Get only items that are in checkout (not saved for later)"""
        return self.order.items.filter(is_saved_for_later=False)
    
    def calculate_final_amount(self):
        """Calculate final amount including service charge and discount"""
        base_amount = self.total_price + self.service_charge
        return base_amount - self.discount_amount
    
    def validate_split_payment(self):
        """Validate that split payment amounts add up to total"""
        if self.payment_method == "Split Payment":
            total_paid = (
                (self.cash_amount or Decimal('0.00')) +
                (self.card_amount or Decimal('0.00')) +
                (self.upi_amount or Decimal('0.00')) +
                (self.other_amount or Decimal('0.00'))
            )
            final_amount = self.calculate_final_amount()
            return abs(total_paid - final_amount) < Decimal('0.01')  # Allow for rounding errors
        return True

    def __str__(self):
        return f"Checkout for Order #{self.order.id} - Token: {self.order.token} - {self.payment_method}"

    class Meta:
        ordering = ['-datetime']


class SavedItems(models.Model):
    """Model to track items saved for future checkout"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='saved_items_log')
    saved_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    saved_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    
    # Track which items were saved
    items_count = models.IntegerField(default=0)
    total_saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    def __str__(self):
        return f"Saved items for Order #{self.order.id} - {self.items_count} items"
    
    class Meta:
        ordering = ['-saved_date']