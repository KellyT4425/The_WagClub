"""Forms for services app."""

from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    """ModelForm with explicit validation for service reviews."""

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"min": 1, "max": 5, "step": 1, "class": "form-control"}
            ),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(
                attrs={"rows": 4, "class": "form-control", "minlength": 20}
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None:
            raise forms.ValidationError("Rating is required.")
        if not 1 <= rating <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if len(body) < 20:
            raise forms.ValidationError("Review must be at least 20 characters.")
        return body
