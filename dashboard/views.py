from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, logout, login
from django.contrib import messages 
from django.contrib.auth.hashers import make_password

from .decorators import store_owner_access
from inventory.models import *
from authentication.models import *
from .forms import MenuForm, TablesForm, StoreAddUserForm
from orders.models import *



def signin(request):
    if request.method == "POST":
        username = request.POST['uname']
        password = request.POST['pswd']
        user1 = authenticate(request, username = username , password = password)
        
        if user1 is not None:
            
            request.session['username'] = username
            request.session['password'] = password
            login(request, user1)
            return redirect('dashboard')
        
        else:
            messages.error(request,'Username or Password Incorrect')
            return redirect('SignIn')
    return render(request,"login.html")


@store_owner_access   
def dashboard(request):
    return render(request, 'index.html')

def SignOut(request):
    logout(request)
    return redirect("signin")




# product functions 

@store_owner_access 
def Add_Category(request):
    if request.method == "POST":
        pic = request.FILES['pic']
        cname = request.POST['cname']
        foodcategory = FoodCategory.objects.create(image = pic, name= cname, store = request.user.store_memberships.all()[0].store )
        foodcategory.save()
        messages.success(request,"Food Category Addedd...")
        return redirect("List_Category")
    
    return render(request,'fooditems/add-category.html')

@store_owner_access 
def List_Category(request):
    store = request.user.store_memberships.all()[0].store
    food_category = FoodCategory.objects.filter(store = store)
   
    context = {
        "food_category":food_category
    }
    return render(request,'fooditems/list-category.html',context)


@store_owner_access 
def EditCategory(request,pk):

    cat = get_object_or_404(FoodCategory, id=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        image = request.FILES.get('image')
        
        if name:
            cat.name = name
        
        if image:
            cat.image = image
        
        try:
            cat.save()
            messages.success(request, 'Category updated successfully')
            return redirect('EditCategory', pk = pk)  
        except Exception as e:
            messages.error(request, f'Error updating category: {e}')
    
    context = {
        'cat': cat,
    }
    return render(request,'fooditems/edit-category.html',context)


@store_owner_access 
def DeleteCategory(request,pk):
    cat = FoodCategory.objects.get(id = pk)
    cat.delete()
    messages.success(request,'Food Category Deleted')
    return redirect('List_Category')



# finished basic testing of category finish category functions ---------------------- 
# finished basic testing of category finish category functions ----------------------
# 
#  tax need to find the testing 
@store_owner_access 
def AddTax(request):
    if request.method == "POST":
        name = request.POST.get('name')
        tax_rate = request.POST.get('tax')
        tax = Tax.objects.create(tax_name = name,tax_percentage = tax_rate )
        tax.save()
        messages.success(request,'Tax Value Added Success')
        return redirect("ListTax")
    return render(request,"add-tax-slab.html")

@store_owner_access 
def ListTax(request):
    tax = Tax.objects.all()

    context = {
        "tax":tax
    }
    return render(request,"list-tax.html",context)


@store_owner_access 
def Add_Product(request):
    if request.method == "POST":
        form = MenuForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.store = request.user.store_memberships.all()[0].store
            menu_item.save()
            messages.success(request,"menu Created")
            return redirect("List_Product")  # replace with your menu list view name
        else:
            messages.error(request,f"Something wrong - Error {form.errors.as_text}")
            return redirect("Add_Product")
    form = MenuForm(user=request.user)
        
    context = {
        "form":form
    }
    return render(request,'fooditems/add-product.html',context)

@store_owner_access 
def List_Product(request):
    menu = Menu.objects.filter(store = request.user.store_memberships.all()[0].store)

    context = {
        "menu":menu,
    }
    return render(request,'fooditems/list-product.html',context)

@store_owner_access 
def EditProduct(request, pk):
    menu_item = get_object_or_404(Menu, id = pk)
    if request.method == "POST":
        form = MenuForm(request.POST, request.FILES, user=request.user,instance = menu_item )
        if form.is_valid():
            menu_item = form.save()
            messages.success(request, 'Menu updated successfully')
            return redirect("List_Product")  # replace with your menu list view name
        else:
            messages.error(request,f"Something wrong - Error {form.errors.as_text}")
            return redirect("EditProduct")
    form = MenuForm(user=request.user, instance = menu_item )
        
    
    context = {
        'form':form
    }
    return render(request, "fooditems/edit-product.html", context)

@store_owner_access 
def DeleteProduct(request,pk):
    menu  = Menu.objects.get(id = pk)
    if menu.status == False:
        menu.status = True
    else:
        menu.status = False
    menu.save()
    messages.info(request,"Product Deleted....")
    return redirect("List_Product")


@store_owner_access 
def Add_Table(request):
    if request.method == "POST":
        tnum = request.POST['tnum']
        seats = request.POST['seats']
        if Tables.objects.filter(Table_number = tnum).exists():
            messages.error(request,"Table Already Exists...")
            return redirect("Add_Table")
        else:
            table = Tables.objects.create(Table_number = tnum, Number_of_Seats = seats)
            table.save()
            messages.success(request,"Table added Success...")
            return redirect("List_Table")

    return render(request,"utils/add-table.html")

@store_owner_access 
def List_Table(request):
    table = Tables.objects.all()
    context = {
        "table":table
    }
    return render(request,"utils/list-table.html",context)


@store_owner_access
def edit_table(request, pk):
    table = get_object_or_404(Tables, id=pk)
    form = TablesForm(instance=table)
    if request.method == "POST":
        form = TablesForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(request, "Table updated successfully.")
            return redirect('List_Table')
        else:
            messages.error(request, "Failed to update table.")
    context = {
        'form': form,
        'table': table,
    }
    return render(request, 'utils/edit_table.html', context)

@store_owner_access 
def Delete_Table(request,pk):
    Tables.objects.get(id = pk).delete()
    messages.success(request,"Table deleted success....")
    return redirect("List_Table")


# user management 

# Get all users of a store where a given user is store_owner
def get_store_users(owner_user):
    try:
        # Find the store(s) where this user is the store_owner
        store_user = StoreUser.objects.get(user=owner_user, role="store_owner")
        store = store_user.store

        # Get all users of the same store
        users = CustomUser.objects.filter(store_memberships__store=store).distinct()
        return users
    except StoreUser.DoesNotExist:
        return CustomUser.objects.none()


@store_owner_access 
def ListUser(request):
    contacts = get_store_users(request.user)

    context = {
        'contacts':contacts
    }

    return render(request,"users/user-list.html",context)


@store_owner_access 
def AddUser(request):
    store = request.user.store_memberships.all()[0].store
    if request.method == "POST":
        form = StoreAddUserForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            user, created = CustomUser.objects.get_or_create(
                email=data["email"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone": data["phone"],
                    "password": make_password(data["password"]),
                },
            )
            # Assign user to store
            StoreUser.objects.get_or_create(
                store=store,
                user=user,
                defaults={"role": data["role"], "assigned_by": request.user}
            )
            messages.success(request, "User added successfully!")
            return redirect("ListUser", store_id=store.id)
    else:
        form = StoreAddUserForm()
    return render(request,"users/user-add.html",{"form": form, "store": store})

@store_owner_access 
def DeleteUser(request,pk):
    CustomUser.objects.get(id = pk).delete()
    messages.success(request,"User Data Deleted.....")
    return redirect("ListUser")


# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from datetime import datetime, timedelta
from orders.models import Order, OrderItem, Checkout
from django.contrib import messages




@store_owner_access 
def list_sale(request):
    # Get user's store
    store = request.user.store_memberships.all()[0].store
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_status_filter = request.GET.get('payment_status', '')
    order_method_filter = request.GET.get('order_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset - only completed orders (sales)
    orders = Order.objects.filter(
        store=store,
        checkout_status=True  # Only orders that have been checked out
    ).select_related('table', 'user').prefetch_related('items__menu_item')
    
    # Apply filters
    if search_query:
        orders = orders.filter(
            Q(token__icontains=search_query) |
            Q(id__icontains=search_query) |
            Q(table__Table_number__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    
    if order_method_filter:
        orders = orders.filter(order_method=order_method_filter)
    
    if date_from:
        orders = orders.filter(create_date__date__gte=date_from)
    
    if date_to:
        orders = orders.filter(create_date__date__lte=date_to)
    
    # Order by latest first
    orders = orders.order_by('-create_date')
    
    # Calculate summary statistics
    total_sales = orders.aggregate(
        total_amount=Sum('total_price'),
        total_orders=Count('id'),
        total_tax=Sum('total_tax')
    )
    
    # Pagination
    paginator = Paginator(orders, 25)  # Show 25 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter choices for dropdowns
    status_choices = Order.status_options
    payment_status_choices = [
        ("Pending", "Pending"), 
        ("Paid", "Paid"), 
        ("Partial", "Partial")
    ]
    order_method_choices = Order.ORDER_METHOD_CHOICES
    
    context = {
        'orders': page_obj,
        'total_sales': total_sales,
        'search_query': search_query,
        'status_filter': status_filter,
        'payment_status_filter': payment_status_filter,
        'order_method_filter': order_method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': status_choices,
        'payment_status_choices': payment_status_choices,
        'order_method_choices': order_method_choices,
        'store': store,
    }
    
    return render(request, 'sales/sales.html', context)


@store_owner_access
def sale_detail(request, order_id):
    """View individual sale details"""
    store = request.user.store_memberships.all()[0].store
    
    # Get the order with all related data
    order = get_object_or_404(
        Order.objects.select_related('table', 'user')
                    .prefetch_related(
                        'items__menu_item__food_category',
                        'items__add_ons',
                        'items__tax'
                    ),
        id=order_id,
        store=store,
        checkout_status=True
    )
    
    # Get checkout details if exists
    checkout = None
    try:
        checkout = order.checkout
    except:
        pass
    
    # Get only items that were in checkout (not saved for later)
    order_items = order.items.filter(is_saved_for_later=False)
    
    # Calculate item-wise totals
    items_with_totals = []
    for item in order_items:
        addon_total = sum(addon.price for addon in item.add_ons.all())
        item_subtotal = (item.price + addon_total) * item.quantity
        
        # Calculate tax for this item
        tax_amount = 0
        for tax in item.tax.all():
            tax_amount += (item_subtotal * tax.tax_percentage) / 100
        
        items_with_totals.append({
            'item': item,
            'addon_total': addon_total,
            'subtotal': item_subtotal,
            'tax_amount': tax_amount,
            'total_with_tax': item_subtotal + tax_amount
        })
    
    context = {
        'order': order,
        'checkout': checkout,
        'items_with_totals': items_with_totals,
        'store': store,
    }
    
    return render(request, 'sales/sale_detail.html', context)


@store_owner_access
def update_order_status(request, order_id):
    """AJAX view to update order status"""
    if request.method == 'POST':
        store = request.user.store_memberships.all()[0].store
        order = get_object_or_404(Order, id=order_id, store=store)
        
        new_status = request.POST.get('status')
        if new_status in dict(Order.status_options):
            order.status = new_status
            order.save()
            return JsonResponse({
                'success': True,
                'message': f'Order status updated to {new_status}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@store_owner_access
def sales_analytics(request):
    """View for sales analytics and reports"""
    store = request.user.store_memberships.all()[0].store
    
    # Get date range (default to last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Get sales data
    sales_data = Order.objects.filter(
        store=store,
        checkout_status=True,
        create_date__date__range=[start_date, end_date]
    ).aggregate(
        total_revenue=Sum('total_price'),
        total_orders=Count('id'),
        total_tax_collected=Sum('total_tax'),
        avg_order_value=Sum('total_price') / Count('id') if Count('id') > 0 else 0
    )
    
    # Sales by method
    sales_by_method = Order.objects.filter(
        store=store,
        checkout_status=True,
        create_date__date__range=[start_date, end_date]
    ).values('order_method').annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('-revenue')
    
    # Top selling items
    top_items = OrderItem.objects.filter(
        order__store=store,
        order__checkout_status=True,
        order__create_date__date__range=[start_date, end_date],
        is_saved_for_later=False
    ).values(
        'menu_item__name',
        'menu_item__food_category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price') * Sum('quantity')
    ).order_by('-total_quantity')[:10]
    
    context = {
        'sales_data': sales_data,
        'sales_by_method': sales_by_method,
        'top_items': top_items,
        'start_date': start_date,
        'end_date': end_date,
        'store': store,
    }
    
    return render(request, 'sales/analytics.html', context)



