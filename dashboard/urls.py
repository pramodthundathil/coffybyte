from django.urls import path 
from .import views 

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path('SignIn',views.signin,name="SignIn"),
    path('SignOut', views.SignOut, name='SignOut'),

    path('Add_Category/', views.Add_Category, name='Add_Category'),
    path('List_Category/', views.List_Category, name='List_Category'),
    path('EditCategory/<int:pk>/', views.EditCategory, name='EditCategory'),
    path('DeleteCategory/<int:pk>/', views.DeleteCategory, name='DeleteCategory'),
    
    path('AddTax/', views.AddTax, name='AddTax'),
    path('ListTax/', views.ListTax, name='ListTax'),
    
    path('Add_Product/', views.Add_Product, name='Add_Product'),
    path('List_Product/', views.List_Product, name='List_Product'),
    path('EditProduct/<int:pk>/', views.EditProduct, name='EditProduct'),
    path('DeleteProduct/<int:pk>/', views.DeleteProduct, name='DeleteProduct'),
    
    path('Add_Table/', views.Add_Table, name='Add_Table'),
    path('List_Table/', views.List_Table, name='List_Table'),
    path("edit_table/<int:pk>", views.edit_table, name="edit_table"),
    path('Delete_Table/<int:pk>/', views.Delete_Table, name='Delete_Table'),

    path("ListUser",views.ListUser,name="ListUser"),
    path("AddUser",views.AddUser,name="AddUser"),
    path("DeleteUser/<uuid:pk>",views.DeleteUser,name="DeleteUser"),

    path('list_sale/',views.list_sale,name="list_sale"),
    # Sales list and detail views
    path('sales/', views.list_sale, name='list_sale'),
    path('sales/<int:order_id>/', views.sale_detail, name='sale_detail'),
    path('sales/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('sales/analytics/', views.sales_analytics, name='sales_analytics'),
    
    # Receipt views (optional - you can implement these later)
    # path('sales/receipt/<int:order_id>/', views.print_receipt, name='print_receipt'),
    # path('sales/receipt/<int:order_id>/pdf/', views.receipt_pdf, name='receipt_pdf'),

     path('reports_dashboard/', views.reports_dashboard, name='reports_dashboard'),
    
    # Report generation endpoints
    path('daybook/', views.generate_daybook, name='generate_daybook'),
    path('sales-summary/', views.generate_sales_summary, name='generate_sales_summary'),
    path('payment-methods/', views.generate_payment_methods, name='generate_payment_methods'),
    path('menu-performance/', views.generate_menu_performance, name='generate_menu_performance'),
    path('tax-report/', views.generate_tax_report, name='generate_tax_report'),
    path('order-status/', views.generate_order_status, name='generate_order_status'),

     path('dashboard/chart-data/<str:chart_type>/', views.dashboard_chart_data, name='dashboard_chart_data'),
    
    # Additional dashboard endpoints you might need
    path('dashboard/refresh-metrics/', views.refresh_metrics, name='refresh_metrics'),
    path('dashboard/export-report/', views.export_dashboard_report, name='export_report'),


    
    # B2B POS URLs - make sure they're properly namespaced
    path('b2b_pos/', views.b2b_pos, name='b2b_pos'),
    path('b2b/create-order/', views.create_b2b_order, name='create_b2b_order'),
    path('b2b/add-item/', views.add_b2b_item, name='add_b2b_item'),
    path('b2b/update-item/', views.update_b2b_item, name='update_b2b_item'),
    path('b2b/remove-item/', views.remove_b2b_item, name='remove_b2b_item'),
    path('b2b/order/<int:order_id>/details/', views.get_b2b_order_details, name='get_b2b_order_details'),
    path('b2b/checkout/', views.checkout_b2b_order, name='checkout_b2b_order'),
    path('b2b/search/', views.search_menu_items, name='search_menu_items'),
    path('b2b/active-orders/', views.get_active_b2b_orders, name='get_active_b2b_orders'),

    # B2B Sales Report URLs (NEW)
    path('pos/b2b/sales/', views.b2b_sales_list, name='b2b_sales_list'),
    path('pos/b2b/invoice/<int:order_id>/', views.b2b_invoice, name='b2b_invoice'),

]

