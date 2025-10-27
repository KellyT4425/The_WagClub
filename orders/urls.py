from django.contrib import admin
from django.urls import path, include
from .views import voucher_invoice

app_name = "orders"
urlpatterns = [
    path('voucher/invoice/<str:code>/',
         voucher_invoice, name='voucher_invoice'),
]
