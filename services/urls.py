from django.contrib import admin
from django.urls import path
from services import views

app_name = "services"
urlpatterns = [
    path('services/', views.service_list, name="service_list"),

]
