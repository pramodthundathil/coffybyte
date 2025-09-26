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
]