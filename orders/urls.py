from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Tables
    path('tables/', views.TableListView.as_view(), name='table-list'),
    
    # Orders
    path('order-list/', views.OrderListView.as_view(), name='order-list'),
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('statistics/', views.order_statistics, name='order-statistics'),
    path('kitchen-display/', views.kitchen_display, name='kitchen-display'),
    
    # Order Items Management
    path('<int:order_id>/manage-items/', views.manage_order_items, name='manage-order-items'),
    path('items/<int:pk>/update/', views.OrderItemUpdateView.as_view(), name='order-item-update'),
    
    # Saved Items
    path('save-ticket/', views.save_ticket, name='save-ticket'),
    path('saved-items/', views.saved_items_list, name='saved-items-list'),
    
    # Checkout & Receipt
    path('checkout/', views.CheckoutCreateView.as_view(), name='checkout-create'),
    path('<int:order_id>/receipt/', views.get_receipt, name='order-receipt'),
     # Tax and Modifier management for order items
    path('order-items/<int:item_id>/taxes-modifiers/', views.add_taxes_modifiers_to_item, name='add-taxes-modifiers-to-item'),
    path('order-items/<int:item_id>/taxes-modifiers/remove/', views.remove_taxes_modifiers_from_item, name='remove-taxes-modifiers-from-item'),
    path('order-items/<int:item_id>/taxes-modifiers/clear/', views.clear_all_taxes_modifiers_from_item, name='clear-taxes-modifiers-from-item'),
    path('order-items/bulk-taxes-modifiers/', views.bulk_add_taxes_modifiers, name='bulk-add-taxes-modifiers'),
]