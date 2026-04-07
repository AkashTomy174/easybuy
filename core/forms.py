from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Banner


class CustomerRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password1", "password2"]


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = [
            "title",
            "description",
            "image",
            "redirect_url",
            "start_date",
            "end_date",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                    "placeholder": "Homepage spotlight title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                    "rows": 4,
                    "placeholder": "Add the supporting text that should appear on this banner.",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                    "accept": "image/*",
                }
            ),
            "redirect_url": forms.URLInput(
                attrs={
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                    "placeholder": "https://example.com/landing-page",
                }
            ),
            "start_date": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "end_date": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-xl border-slate-200 bg-white",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_date"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        image = cleaned_data.get("image")

        if start_date and end_date and end_date <= start_date:
            self.add_error("end_date", "End date must be later than the start date.")
        if not image and not getattr(self.instance, "image", None):
            self.add_error("image", "Please upload a banner image.")

        return cleaned_data
