from django.contrib import admin
from .models import Order, OrderItem, Voucher

# Register your models here.
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Voucher)
admin.site.site_header = "Order Management Admin"
