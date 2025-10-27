from django.shortcuts import render, get_object_or_404
from .models import Voucher

# Create your views here.


def voucher_invoice(request, code):

    try:
        voucher = Voucher.objects.get(code=code)
    except Voucher.DoesNotExist:
        return render(request, 'orders/vouc_not_found.html', {'code': code})

    context = {
        'voucher': voucher,
        'user': voucher.user,
        'service': voucher.service,

    }

    return render(request, 'voucher/invoice.html', context)
