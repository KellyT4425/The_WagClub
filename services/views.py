from django.shortcuts import render
from .models import Service


# Create your views here.


def home(request):
    return render(request, 'home.html')


def service_list(request):
    passes = Service.objects.filter(
        is_active=True, category__slug="doggy_daycare_pass").select_related("category").order_by("price")
    packages = Service.objects.filter(
        is_active=True, category__slug="doggy_grooming_packs").select_related("category").order_by("price")
    offers = Service.objects.filter(
        is_active=True, category__slug="pet_offers").select_related("category").order_by("price")

    context = {
        "doggy_daycare_pass": passes,
        "doggy_grooming_packs": packages,
        "pet_offers": offers,
    }

    return render(request, "services/service_list.html", context)
