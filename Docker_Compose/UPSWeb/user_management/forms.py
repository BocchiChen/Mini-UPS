from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UPSAccount, Package_Info

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(max_length=20, error_messages={'max_length':'Length must be within 20', 'required':'username is required'}, 
        widget = forms.TextInput(attrs={'placeholder':'username', 'class':'form-control'}), label='username')

    password1 = forms.CharField(error_messages={'required':'password is required'}, 
        widget = forms.PasswordInput(attrs={'placeholder':'password', 'class':'form-control'}), label='password1')

    password2 = forms.CharField(error_messages={'required':'password is required'}, 
        widget = forms.PasswordInput(attrs={'placeholder':'password', 'class':'form-control'}), label='password2')

    ups_account_number = forms.CharField(error_messages={'required':'ups account number is required'}, 
        widget = forms.TextInput(attrs={'placeholder':'please enter the same account number with Amazon', 'class':'form-control'}), label='ups_account_number')
   
    email = forms.EmailField(error_messages={'required':'email is required'}, 
        widget = forms.EmailInput(attrs={'placeholder':'email', 'class':'form-control'}), label='email')


    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'ups_account_number', 'email']

class UPSAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

class PackageInfoForm(forms.ModelForm):
    class Meta:
        model = Package_Info
        fields = ['package_id', 'count', 'ship_id', 'truck', 'status',
                  "destination_x", "destination_y", "warehouse_id", "description"]
        
class PackageEditForm(forms.ModelForm):
    class Meta:
        model = Package_Info
        fields = ["destination_x", "destination_y"]