
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomerRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password1', 'password2']

