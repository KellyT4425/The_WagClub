from django.db import models
from services.models import Service
from django.contrib.auth import get_user_model
from django.utils import timezone
from dateutil.relativedelta import relativedelta


# Create your models here.
VOUC_STATUS = [
    ("ISSUED", "ISSUED"),
    ("REDEEMED", "REDEEMED"),
    ("EXPIRED", "EXPIRED")
]

User = get_user_model()


def default_expiry():
    return timezone.now() + relativedelta(months=18)


class Order(models.Model):
    user = models.ForeignKey(
        # adding plural suggests one user many "orders".
        User, on_delete=models.CASCADE, related_name="orders")
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)


class OrderItem(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="order_items")
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items")
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


class Voucher(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="vouchers")
    order_item = models.ForeignKey(
        "OrderItem", on_delete=models.CASCADE, related_name="vouchers")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="vouchers")
    code = models.CharField(max_length=16, unique=True)
    qr_img_path = models.ImageField(
        upload_to='vouchers/qr_codes/', null=True, blank=True)
    status = models.CharField(choices=VOUC_STATUS, max_length=20)
    issued_at = models.DateTimeField(auto_now_add=True)
    redeemed_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(default=default_expiry)

    class Meta:
        ordering = ['-issued_at']
