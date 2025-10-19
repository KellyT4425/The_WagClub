from django.contrib import admin
from django.urls import path, include
from services import views

urlpatterns = [
    path('services/', views.service_list, name="service_list"),

]
