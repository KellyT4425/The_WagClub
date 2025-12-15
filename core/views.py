from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import NewsletterSignupForm


def custom_404(request, exception):
    """Render custom 404 page."""
    return render(request, "404.html", status=404)


def custom_500(request):
    """Render custom 500 page."""
    return render(request, "500.html", status=500)


def custom_400(request, exception=None):
    """Render custom 400 bad request page."""
    return render(request, "400.html", status=400)


def custom_403(request, exception=None):
    """Render custom 403 forbidden page."""
    return render(request, "403.html", status=403)


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
