from django.urls import path
from . import views


app_name = "orders"

urlpatterns = [
    path('cart/', views.cart, name='cart'),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path('cart/remove/<str:item_id>/',
         views.remove_from_cart, name='remove_from_cart'),

    path('voucher/invoice/<str:code>/',
         views.voucher_invoice, name='voucher_invoice'),
    path('checkout/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('voucher/<str:code>/', views.voucher_detail, name='voucher_detail'),
    path("voucher/<str:code>/redeem/",
         views.redeem_voucher, name="redeem_voucher"),

    # Add a path for creating checkout sessions
    path('checkout/create-session/', views.create_checkout_session,
         name='create_checkout_session'),
    # Change the names to match what you're using in the reverse() function
    path('success/', views.success_view, name='success'),
    path('cancel/', views.cancel_view, name='cancel'),
    path('my-wallet/', views.my_wallet, name='my_wallet'),
]
