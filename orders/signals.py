# Signal to update order totals when items change
from .models import OrderItem
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_totals_on_item_change(sender, instance, **kwargs):
    """Update order totals when items are added/removed/modified"""
    if hasattr(instance, 'order'):
        instance.order.calculate_totals()
        instance.order.save(update_fields=['total_price', 'total_tax', 'total_before_tax'])

@receiver(m2m_changed, sender=OrderItem.add_ons.through)
@receiver(m2m_changed, sender=OrderItem.tax.through)
def update_order_totals_on_m2m_change(sender, instance, **kwargs):
    """Update order totals when addons or taxes are modified"""
    if kwargs['action'] in ['post_add', 'post_remove', 'post_clear']:
        instance.order.calculate_totals()
        instance.order.save(update_fields=['total_price', 'total_tax', 'total_before_tax'])