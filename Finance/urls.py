from django.urls import path 
from .import views

urlpatterns = [
    path("income",views.income, name= "income"),
    path("expence",views.expence, name= "expence"),
    path("balance_sheet",views.balance_sheet, name= "balance_sheet"),
    path("balance_sheet_selected",views.balance_sheet_selected, name= "balance_sheet_selected"),
    path('add_income/', views.add_income, name='add_income'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('delete_income/<int:pk>', views.delete_income, name='delete_income'),
    path('delete_expense/<int:pk>', views.delete_expense, name='delete_expense'),
    path('update_income/<int:pk>', views.update_income, name='update_income'),
    path('update_expense/<int:pk>', views.update_expense, name='update_expense'),


    # reports

    path('expence_report_excel/', views.expence_report_excel, name='expence_report_excel'),
    path('expence_report_pdf/', views.expence_report_pdf, name='expence_report_pdf'),
    path('income_report_excel/', views.income_report_excel, name='income_report_excel'),
    path('income_report_pdf/', views.income_report_pdf, name='income_report_pdf'),
   

    #DB download.......................

    path("download_db",views.download_db,name="download_db"),
    
    
]