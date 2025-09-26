from django import forms
from .models import Income, Expence

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['perticulers', 'amount', "bill_number", 'other']
        labels = {
            'perticulers': 'Particulars',
            'amount': 'Amount',
            'other': 'Partner Details',
        }
        widgets = {
            'perticulers': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'income-perticulers',
                'placeholder': 'Enter particulars'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'income-amount',
                'placeholder': 'Enter amount',
                "min":0
            }),
            'other': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'income-other',
                'placeholder': 'Other details'
            }),
            'bill_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'billno',
                'placeholder': 'Bill Number (Optional)'
            }),
        }

class ExpenceForm(forms.ModelForm):
    class Meta:
        model = Expence
        fields = ['perticulers',"bill_number", 'amount', 'other']
        labels = {
            'perticulers': 'Particulars',
            'amount': 'Amount',
            'other': 'Partner Details',
        }
        widgets = {
            'perticulers': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'expence-perticulers',
                'placeholder': 'Enter particulars'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'expence-amount',
                'placeholder': 'Enter amount',
                "min":0
            }),
            'other': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'expence-other',
                'placeholder': 'Other details',
               
            }),
            'bill_number': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'billno',
                'placeholder': 'Bill Number (Optional)'
            }),
        }
