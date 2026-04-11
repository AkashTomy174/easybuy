from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
)
from .models import User, Banner


AUTH_INPUT_CLASS = (
    "w-full px-5 py-3 bg-stone-50 dark:bg-stone-900/50 border "
    "border-stone-200 dark:border-stone-700 rounded-2xl text-stone-900 "
    "dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary "
    "transition-all outline-none"
)


class StyledAuthFormMixin:
    field_placeholders = {}

    def _apply_auth_styles(self):
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", AUTH_INPUT_CLASS)
            if name in self.field_placeholders:
                field.widget.attrs.setdefault("placeholder", self.field_placeholders[name])


class ForgotPasswordForm(StyledAuthFormMixin, forms.Form):
    email = forms.EmailField()
    field_placeholders = {"email": "Enter your account email"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_auth_styles()


class EasyBuySetPasswordForm(StyledAuthFormMixin, SetPasswordForm):
    field_placeholders = {
        "new_password1": "Create a new password",
        "new_password2": "Confirm your new password",
    }

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self._apply_auth_styles()


class EasyBuyPasswordChangeForm(StyledAuthFormMixin, PasswordChangeForm):
    field_placeholders = {
        "old_password": "Enter your current password",
        "new_password1": "Create a new password",
        "new_password2": "Confirm your new password",
    }

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self._apply_auth_styles()


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
