from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


urlpatterns = [
    # Tax URLs
    path('taxes/', views.TaxListCreateView.as_view(), name='tax-list-create'),
    path('taxes/<int:pk>/', views.TaxRetrieveUpdateDestroyView.as_view(), name='tax-detail'),
    
    # Modifier URLs
    path('modifiers/', views.ModifierListCreateView.as_view(), name='modifier-list-create'),
    path('modifiers/<int:pk>/', views.ModifierRetrieveUpdateDestroyView.as_view(), name='modifier-detail'),
    
    # Modifier Options URLs
    path('modifiers/<int:modifier_id>/options/', views.ModifierOptionsListCreateView.as_view(), name='modifier-options-list-create'),
    path('modifier-options/<int:pk>/', views.ModifierOptionsRetrieveUpdateDestroyView.as_view(), name='modifier-options-detail'),
    
    # Food Category URLs
    path('categories/', views.FoodCategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', views.FoodCategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),
    
    # Menu URLs
    path('menu/', views.MenuListCreateView.as_view(), name='menu-list-create'),
    path('menu/<int:pk>/', views.MenuRetrieveUpdateDestroyView.as_view(), name='menu-detail'),
    
    # Additional Menu URLs
    path('menu/by-category/<int:category_id>/', views.menu_by_category, name='menu-by-category'),
    path('menu/bulk-update-status/', views.bulk_update_menu_status, name='menu-bulk-update-status'),
    path('menu/search/', views.search_menu_items, name='menu-search'),
    path('menu/<int:menu_id>/duplicate/', views.duplicate_menu_item, name='menu-duplicate'),
    
    # Dashboard
    path('dashboard/', views.menu_dashboard, name='menu-dashboard'),
]