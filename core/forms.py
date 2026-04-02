from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, AdBooking


class CustomerRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password1", "password2"]


class AdBookingForm(forms.ModelForm):
    class Meta:
        model = AdBooking
        fields = ["image", "redirect_url", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-xl border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-xl border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800",
                }
            ),
            "redirect_url": forms.URLInput(
                attrs={
                    "class": "w-full rounded-xl border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800",
                    "placeholder": "https://",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "w-full text-sm text-stone-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-primary file:text-white hover:file:bg-primary-dark"
                }
            ),
        }
