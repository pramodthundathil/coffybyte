from django import forms
from inventory.models import Menu, FoodCategory
from orders.models import Tables

class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = [
            "category", "name", "image", "portion", "diet", "price", 
            "status", "stock", "description", "code", "taxes"
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "portion": forms.Select(attrs={"class": "form-control"}),
            "diet": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "taxes": forms.Select(attrs={"class": "form-control"}),
            
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # get user from view
        super(MenuForm, self).__init__(*args, **kwargs)

        if user:
            # Get the store for this user
            store = user.store_memberships.all()[0].store
            # Filter categories for this store
            self.fields["category"].queryset = FoodCategory.objects.filter(store=store)


class TablesForm(forms.ModelForm):
    class Meta:
        model = Tables
        fields = ['Table_number', 'Number_of_Seats', 'status']
        widgets = {
            'Table_number': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter table number'}),
            'Number_of_Seats': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter number of seats'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from authentication.models import StoreUser

User = get_user_model()

class StoreAddUserForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name", "id": "fname"})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name", "id": "lname"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email", "id": "email"})
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+911234567890", "id": "phone"})
    )
    role = forms.ChoiceField(
        choices=StoreUser.STORE_ROLES,
        widget=forms.Select(attrs={"class": "selectpicker form-control", "data-style": "py-0"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password", "id": "pass"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repeat Password", "id": "rpass"})
    )
    profile_pic = forms.ImageField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get("password")
        pwd2 = cleaned_data.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data
