from django.shortcuts import render, redirect
from  django.contrib import messages 
from django.contrib.auth import logout

def store_owner_access(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            user = request.user
            try:
                if user.store_memberships.all()[0].role == 'store_owner':
                    return view_func(request, *args, **kwargs)
                else:
                    
                    # messages.info(request,"")
                    return redirect('b2b_pos')
            except:
                logout(request)
                messages.info(request,"Something Wrong")
                return redirect('SignIn')

        else:
            messages.info(request, 'Please Login to access this page')
            return redirect('SignIn')
    
    return wrapper_func 
