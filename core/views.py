from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import NewsletterSignupForm


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)


def newsletter_subscribe(request):
    """Handle newsletter signup."""
    if request.method != "POST":
        return redirect("home")

    form = NewsletterSignupForm(request.POST)
    if form.is_valid():
        try:
            form.save()
            messages.success(request, "Thanks for subscribing!")
        except IntegrityError:
            messages.info(request, "That email is already subscribed.")
    else:
        messages.error(request, "Please enter a valid email address.")

    return redirect(request.META.get("HTTP_REFERER", reverse("home")))
