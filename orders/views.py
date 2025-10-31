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
        cart = request.session.get("cart", {})

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")

    line_items = []
    for item_id, item_data in cart.items():
        price_cents = int(Decimal(str(item_data["price"])) * 100)
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": item_data["name"]},
                "unit_amount": price_cents,
            },
            "quantity": item_data["quantity"],
        })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('orders:success')),
                cancel_url=request.build_absolute_uri(reverse('orders:cart')),
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            messages.error(
                request, f"Error creating checkout session: {str(e)}")
            return redirect('orders:cart')

    return redirect('orders:cart')


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


def remove_from_cart(request, item_id):
    cart = request.session.get("cart", {})

    print(f"Current cart contents: {cart}")

    if item_id in cart:
        del cart[item_id]
        request.session["cart"] = cart
        request.session.modified = True
        messages.info(request, "Item removed from cart successfully.")
    else:
        # Add specific message if item wasn't found
        messages.error(request, f"Item {item_id} was not found in your cart.")

    return redirect("orders:cart")


def cart(request):
    """Build the context shape your template expects."""
    cart = request.session.get(
        "cart", {})  # { "12": {name, price, quantity}, ... }
    cart_items = []
    total_amount = 0.0

    # Fetch the products and create cart items
    for item_id, item_data in cart.items():
        item_total = float(item_data["price"]) * int(item_data["quantity"])
        total_amount += item_total

        cart_items.append({
            "id": item_id,  # Keep the ID for removal
            "name": item_data["name"],
            "price": item_data["price"],
            "quantity": item_data["quantity"],
        })

    context = {"cart_items": cart_items, "total_amount": total_amount}
    return render(request, "orders/cart.html", context)
