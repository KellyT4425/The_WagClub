from django import forms
from django.core.validators import RegexValidator
from allauth.account.forms import SignupForm
from allauth.account.forms import LoginForm
from .models import NewsletterSignup


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "Username"
        self.fields["login"].widget.attrs["placeholder"] = "Username"


name_validator = RegexValidator(
    r'^[A-Za-z\s]+$', "Only letters and spaces are allowed.")

username_validator = RegexValidator(
    regex=r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$',
    message="Username can only contain both letters and numbers.",
    code="invalid_username"
)


class CustomSignupForm(SignupForm):
    username = forms.CharField(
        max_length=10,
        required=True,
        validators=[username_validator],
        widget=forms.TextInput(attrs={
            "pattern": r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$",
            "title": "Only letters and numbers are allowed."
        })
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        validators=[name_validator],
        widget=forms.TextInput(attrs={
            "pattern": r"[A-Za-z ]+",
            "title": "Only letters and spaces are allowed."})
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        validators=[name_validator],
        widget=forms.TextInput(attrs={
            "pattern": r"[A-Za-z ]+",
            "title": "Only letters and spaces are allowed."
        })
    )

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['username']
        user.save()
        return user


class NewsletterSignupForm(forms.ModelForm):
    """Simple newsletter subscription form."""

    class Meta:
        model = NewsletterSignup
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
        }
