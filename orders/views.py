from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from services.models import Service
from .models import Voucher, Order, OrderItem
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


def create_checkout_session(request):
    if request.method != "POST":
        return redirect("orders:cart")

    cart = request.session.get("cart", {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")

    line_items = []
    for _sid, item in cart.items():
        price_cents = int(Decimal(str(item["price"])) * 100)
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": item["name"]},
                "unit_amount": price_cents,
            },
            "quantity": int(item["quantity"]),
        })

    checkout_session = stripe.checkout.Session.create(
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(reverse("orders:success")),
        cancel_url=request.build_absolute_uri(reverse("orders:cancel")),
    )

    return redirect(checkout_session.url)


@csrf_exempt  # Stripe isn't a browser, so skip CSRF protection
def stripe_webhook(request):
    STRIPE_WEBHOOK = settings.STRIPE_WEBHOOK
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature (forged or incorrect secret)
        return HttpResponse(status=400)

    # Handle the event types you care about:
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        try:
            # Extract metadata
            service_id = session.metadata.get('service_id')
            user_id = session.metadata.get('user_id')

            if not service_id or not user_id:
                print("Missing metadata in session")
                return HttpResponse(status=400)

            # Get service and user

            service = Service.objects.get(id=service_id)
            user = User.objects.get(id=user_id)

            # Create order
            order = Order.objects.create(
                user=user,
                service=service
            )

            # Create order item
            order_item = OrderItem.objects.create(
                order=order,
                service=service
            )

            # Generate a unique voucher code
            voucher_code = str(uuid.uuid4())[:16]

            # Create a voucher
            voucher = Voucher(
                service=service,
                order_item=order_item,
                user=user,
                code=voucher_code,
                status="ISSUED"
            )

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(voucher_code)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            # Save the QR code image to the voucher
            voucher.qr_img_path.save(
                f"voucher_qr_{voucher_code}.png",
                ContentFile(buffer.getvalue()),
                save=False
            )

            # Save the voucher
            voucher.save()

            # Store voucher_id in a session variable for retrieval on success page
            # Note: This won't work directly in webhook context, you'd need another solution

            print(f"Payment completed! Voucher created: {voucher_code}")
            order.is_paid = True
            order.save()

        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return HttpResponse(status=400)

    return HttpResponse(status=200)


def success_view(request):
    """Display success page after successful checkout"""
    # Try to get the most recent paid order for this user
    if request.user.is_authenticated:
        recent_order = Order.objects.filter(
            user=request.user,
            is_paid=True
        ).order_by('-created_at').first()

        recent_voucher = None
        if recent_order:
            recent_voucher = Voucher.objects.filter(order=recent_order).first()

        context = {
            'order': recent_order,
            'voucher': recent_voucher,
        }
    else:
        context = {}

    return render(request, 'orders/success.html', context)


def cancel_view(request):
    """Display page when checkout is canceled"""
    return render(request, 'orders/cancel.html')


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


def add_to_cart(request):
    if request.method != "POST":
        return redirect("orders:cart")

    service_id = request.POST.get("service_id")
    qty = int(request.POST.get("quantity", 1))
    service = get_object_or_404(Service, id=service_id, is_active=True)

    cart = request.session.get("cart", {})
    key = str(service.id)

    if key in cart:
        cart[key]["quantity"] += max(qty, 1)
    else:
        cart[key] = {
            "name": service.name,
            # stored once; never trust client values
            "price": float(service.price),
            "quantity": max(qty, 1),
        }

    request.session["cart"] = cart
    request.session.modified = True
    messages.success(request, f"Added {service.name} to your cart.")
    return redirect(request.META.get("HTTP_REFERER", "orders:cart"))


def cart(request):
    """Build the context shape your template expects."""
    cart_src = request.session.get(
        "cart", {})  # { "12": {name, price, quantity}, ... }
    cart_items = []
    total_amount = 0.0

    for sid, item in cart_src.items():
        line_total = float(item["price"]) * int(item["quantity"])
        total_amount += line_total
        cart_items.append({
            "id": int(sid),
            "product": {               # ✅ your template expects product.*
                "name": item["name"],
                "price": float(item["price"]),
            },
            "quantity": int(item["quantity"]),
            "total_price": line_total,  # ✅ your template expects this field
        })

    context = {"cart_items": cart_items, "total_amount": total_amount}
    return render(request, "orders/cart.html", context)


def remove_from_cart(request, item_id):
    cart = request.session.get("cart", {})
    key = str(item_id)
    if key in cart:
        del cart[key]
        request.session["cart"] = cart
        request.session.modified = True
        messages.info(request, "Removed item from cart.")
    return redirect("orders:cart")
