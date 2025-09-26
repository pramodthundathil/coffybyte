from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib import messages
from .models import *

from .forms import *
from django.shortcuts import render
from django.utils.timezone import now
from .models import Income, Expence
from itertools import chain
from operator import attrgetter
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required 


@login_required(login_url="SignIn")
def income(request):
    income = Income.objects.all().order_by("-id")

    context = {
        "income":income
    }
    return render(request,"finance/income.html",context)


@login_required(login_url="SignIn")
def add_income(request):
    form = IncomeForm()

    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Income record added successfully.")
            return redirect('income')  # Redirect to the same page or another view
 
    return render(request, 'finance/add-income.html', {'form': form})

@login_required(login_url="SignIn")
def update_income(request,pk):
    income  = get_object_or_404(Income,id = pk)
    form = IncomeForm(instance=income)

    if request.method == 'POST':
        form = IncomeForm(request.POST,instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, "Income Update successfully.")
            return redirect('income')  # Redirect to the same page or another view
 
    return render(request, 'finance/update-income.html', {'form': form})


@login_required(login_url="SignIn")
def delete_income(request,pk):
    income = get_object_or_404(Income,id = pk)
    income.delete()
    messages.success(request,"Income deleted success.....")
    return redirect("income")



@login_required(login_url="SignIn")
def expence(request):
    ex = Expence.objects.all().order_by("-id")
    context = {
        "expence":ex
    }
    return render(request,"finance/expence.html",context)


@login_required(login_url="SignIn")
def delete_expense(request,pk):
    expense = get_object_or_404(Expence,id = pk)
    expense.delete()
    messages.success(request,"Expense deleted success.....")
    return redirect("expence")


# View for adding expense
def add_expense(request):
    if request.method == 'POST':
        form = ExpenceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense record added successfully.")
            return redirect('expence')  # Redirect to the same page or another view
    else:
        form = ExpenceForm()
    return render(request, 'finance/add-expense.html', {'form': form})

def update_expense(request,pk):
    expense = get_object_or_404(Expence, id = pk)
    if request.method == 'POST':
        form = ExpenceForm(request.POST,instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense record added successfully.")
            return redirect('expence')  # Redirect to the same page or another view
    else:
        form = ExpenceForm(instance=expense)
    return render(request, 'finance/update-expense.html', {'form': form})




def balance_sheet(request):
    # Get the current date
    current_date = now()
    month = current_date.strftime("%B")

    # Filter income and expenses for the current month
    income_list = Income.objects.filter(date__year=current_date.year, date__month=current_date.month)
    expense_list = Expence.objects.filter(date__year=current_date.year, date__month=current_date.month)

    # Convert to lists with 'type' field indicating credit (income) or debit (expense)
    income_data = [{'type': 'credit', 'date': income.date, 'perticulers': income.perticulers, 'amount': income.amount} for income in income_list]
    expense_data = [{'type': 'debit', 'date': expense.date, 'perticulers': expense.perticulers, 'amount': expense.amount} for expense in expense_list]

    # Combine both lists and order by date
    combined_list = sorted(
        chain(income_data, expense_data),
        key=lambda x: x['date']
    )

    # Calculate totals
    total_income = sum(income['amount'] for income in income_data)
    total_expense = sum(expense['amount'] for expense in expense_data)

    # Pass data to the template
    return render(request, "finance/balancesheet.html", {
        'combined_list': combined_list,
        'total_income': total_income,
        'total_expense': total_expense,
        "month":month
    })


from django.shortcuts import render
from django.utils.timezone import now
from .models import Income, Expence
from itertools import chain
from operator import attrgetter

def balance_sheet_selected(request):
    if request.method == "POST":
    # Get start and end dates from form submission (default to current month if not provided)
        start_date = request.POST.get('sdate')
        end_date = request.POST.get('edate')

    if start_date and end_date:
        # Filter by selected date range
        income_list = Income.objects.filter(date__range=[start_date, end_date])
        expense_list = Expence.objects.filter(date__range=[start_date, end_date])
    else:
        # Default to current month if no dates are provided
        current_date = now()
        income_list = Income.objects.filter(date__year=current_date.year, date__month=current_date.month)
        expense_list = Expence.objects.filter(date__year=current_date.year, date__month=current_date.month)

    # Convert to lists with 'type' field indicating credit (income) or debit (expense)
    income_data = [{'type': 'credit', 'date': income.date, 'perticulers': income.perticulers, 'amount': income.amount} for income in income_list]
    expense_data = [{'type': 'debit', 'date': expense.date, 'perticulers': expense.perticulers, 'amount': expense.amount} for expense in expense_list]

    # Combine both lists and order by date
    combined_list = sorted(
        chain(income_data, expense_data),
        key=lambda x: x['date']
    )

    # Calculate totals
    total_income = sum(income['amount'] for income in income_data)
    total_expense = sum(expense['amount'] for expense in expense_data)

    # Pass data to the template
    return render(request, "finance/balancesheet.html", {
        'combined_list': combined_list,
        'total_income': total_income,
        'total_expense': total_expense,
        'start_date': start_date,
        'end_date': end_date,
        "month": f"{start_date} to {end_date}"
    })



# in finance i am desided to add report generation through this application 
# below methods are the report generation 



from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.http import HttpResponse
from io import BytesIO
import pandas as pd
from openpyxl.styles import Border, Side
from django.db.models import Sum

def expence_report_excel(request):
    if request.method == "POST":
        # Get the start and end date from the form
        start_date = request.POST['sdate']
        end_date = request.POST['edate']

        # Filter expenses based on the date range
        expenses = Expence.objects.filter(date__range=[start_date, end_date])

        # Convert expenses to a Pandas DataFrame
        data = {
            'Date': [exp.date for exp in expenses],
            'Particulars': [exp.perticulers for exp in expenses],
            'Amount': [exp.amount for exp in expenses],
            'Other': [exp.other for exp in expenses],
        }
        df = pd.DataFrame(data)

        # Create an HttpResponse object with Excel content type
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="expense_report_{start_date}_to_{end_date}.xlsx"'

        # Write the DataFrame to an Excel file
        df.to_excel(response, index=False, engine='openpyxl')

        return response


def expence_report_pdf(request):
   
    if request.method == "POST":
        # Get the start and end date from the form
        start_date = request.POST['sdate']
        end_date = request.POST['edate']
        # logo_url = request.build_absolute_uri(profile.logo.url) if profile and profile.logo else None

        # Filter expenses based on the date range
        expenses = Expence.objects.filter(date__range=[start_date, end_date])
        # Calculate subtotal for amount
        subtotal = expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    
        # Render the data to a template
        template_path = 'expence_report_pdf.html'
        context = {
            'expenses': expenses,
            'start_date': start_date,
            'end_date': end_date,
            # "profile":profile,
            "subtotal":subtotal,
            
        }
        html = render_to_string(template_path, context)

        # Create a PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="expense_report_{start_date}_to_{end_date}.pdf"'

        # Create PDF using xhtml2pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response
        )

        # If there's an error, show it in the response
        if pisa_status.err:
            return HttpResponse('We had some errors with the report')

        return response


def income_report_excel(request):
    if request.method == "POST":
        # Get the start and end date from the form
        start_date = request.POST['sdate']
        end_date = request.POST['edate']

        # Filter expenses based on the date range
        expenses = Income.objects.filter(date__range=[start_date, end_date])
        
        # Convert expenses to a Pandas DataFrame
        data = {
            'Date': [exp.date for exp in expenses],
            'Particulars': [exp.perticulers for exp in expenses],
            'Amount': [exp.amount for exp in expenses],
            'Other': [exp.other for exp in expenses],
        }
        df = pd.DataFrame(data)

        # Create an HttpResponse object with Excel content type
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Income_report_{start_date}_to_{end_date}.xlsx"'

        # Write the DataFrame to an Excel file
        df.to_excel(response, index=False, engine='openpyxl')

        return response


def income_report_pdf(request):
   

    if request.method == "POST":
        # Get the start and end date from the form
        start_date = request.POST['sdate']
        end_date = request.POST['edate']

        # Filter expenses based on the date range
        income = Income.objects.filter(date__range=[start_date, end_date])
        

        subtotal = income.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
        # Render the data to a template
        template_path = 'income_report_pdf.html'
        context = {
            'income': income,
            'start_date': start_date,
            'end_date': end_date,
           
            "subtotal":subtotal
        }
        html = render_to_string(template_path, context)

        # Create a PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="income_report_{start_date}_to_{end_date}.pdf"'

        # Create PDF using xhtml2pdf
        pisa_status = pisa.CreatePDF(
            html, dest=response
        )

        # If there's an error, show it in the response
        if pisa_status.err:
            return HttpResponse('We had some errors with the report')

        return response
    




from django.http import HttpResponse, Http404
import os
from django.conf import settings

def download_db(request):
    # Path to your SQLite database file
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    
    # Check if the file exists
    if os.path.exists(db_path):
        with open(db_path, 'rb') as db_file:
            response = HttpResponse(db_file.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = 'attachment; filename="db.sqlite3"'
            return response
    else:
        raise Http404("Database not found.")






