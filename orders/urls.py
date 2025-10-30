from django.contrib import admin
from django.urls import path, include
from . import views
from .views import voucher_invoice, cart

app_name = "orders"
urlpatterns = [
    path('voucher/invoice/<str:code>/',
         voucher_invoice, name='voucher_invoice'),
    path('cart/', views.cart, name='cart'),
]
