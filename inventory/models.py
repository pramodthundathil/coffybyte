from django.db import models
from authentication.models import Store


class Tax(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    tax_name = models.CharField(max_length=20)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}  {} %'.format(str(self.tax_name), (self.tax_percentage))

    class Meta:
        unique_together = ['store', 'tax_name']


class Modifiers(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    price = models.FloatField(default=0)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['store', 'name']


class ModifierOptions(models.Model):
    modifier = models.ForeignKey(Modifiers, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.modifier.name} - {self.name}"


class FoodCategory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    image = models.FileField(upload_to='category_images', null=True, blank=True)
    date_added = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.name)
    
    class Meta:
        unique_together = ['store', 'name']
        verbose_name_plural = "Food Categories"


class Menu(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category = models.ForeignKey('FoodCategory', on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    image = models.FileField(upload_to='foodimage', null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)

    PORTION_CHOICES = [
        ("Small", "Small"), 
        ("Medium", "Medium"), 
        ("Large", "Large")
    ]
    portion = models.CharField(max_length=255, choices=PORTION_CHOICES)

    DIET_CHOICES = [
        ("Veg", "Veg"), 
        ("Non-Veg", "Non-Veg"), 
        ("Egg", "Egg")
    ]
    diet = models.CharField(max_length=20, choices=DIET_CHOICES)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.BooleanField(default=True)

    stock_track = models.BooleanField(default=False)
    stock = models.IntegerField(null=True, blank=True)
    stock_alert = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    create_date = models.DateField(auto_now_add=True)

    # Code of product for searching
    code = models.CharField(max_length=10, null=True, blank=True, unique=True)
    barcode = models.CharField(max_length=100, null=True, blank=True)

    # Tax fields - supporting multiple taxes
    taxes = models.ManyToManyField(Tax, blank=True, related_name='menu_items')
    
    # Modifier fields - supporting multiple modifiers
    modifiers = models.ManyToManyField(Modifiers, blank=True, related_name='menu_items')

    # Calculated fields
    price_before_tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def calculate_tax_details(self):
        """Calculate price before tax and total tax amount"""
        if self.price is not None:
            total_tax_percentage = sum([tax.tax_percentage for tax in self.taxes.all()])
            if total_tax_percentage > 0:
                tax_multiplier = 1 + (total_tax_percentage / 100)
                self.price_before_tax = round(self.price / tax_multiplier, 2)
                self.total_tax_amount = round(self.price - self.price_before_tax, 2)
            else:
                self.price_before_tax = self.price
                self.total_tax_amount = 0.00
        else:
            self.price_before_tax = 0.00
            self.total_tax_amount = 0.00

    def save(self, *args, **kwargs):
        # Save first to get an ID for M2M relationships
        is_new = self.pk is None
        super(Menu, self).save(*args, **kwargs)
        
        # Calculate tax details after saving (when M2M relationships are available)
        if not is_new:
            self.calculate_tax_details()
            # Update only the calculated fields to avoid recursion
            Menu.objects.filter(pk=self.pk).update(
                price_before_tax=self.price_before_tax,
                total_tax_amount=self.total_tax_amount
            )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['store', 'name', 'portion']