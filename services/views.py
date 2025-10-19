from django.shortcuts import render
from .models import Service, ServiceCategory


# Create your views here.


def home(request):
    return render(request, 'home.html')


def service_list(request):
    return render(request, 'services/service_list.html')
