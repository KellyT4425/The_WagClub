from django.contrib import admin
from django.urls import path, include
from . import views
from .views import voucher_invoice, cart

app_name = "orders"
urlpatterns = [
    path('voucher/invoice/<str:code>/',
         voucher_invoice, name='voucher_invoice'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('', views.cart, name='cart'),
    # Add a path for creating checkout sessions
    path('create-checkout-session/<int:service_id>/', views.create_checkout_session,
         name='create_checkout_session'),
    # Add success and cancel pages
    path('success/', views.success_view, name='checkout_success'),
    path('cancel/', views.cancel_view, name='checkout_cancel'),
]
