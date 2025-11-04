from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from services.models import Service
from .models import Voucher, Order, OrderItem
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import stripe
import uuid
import ast
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
    metadata = {'cart_items': []}

    for item_id, item_data in cart.items():
        price_cents = int(Decimal(str(item_data["price"])) * 100)
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": item_data["name"], "metadata": {
                    "service_id": item_id, "user_id": str(request.user.id)}
                },
                "unit_amount": price_cents,
            },
            "quantity": item_data["quantity"],
        })

        metadata['cart_items'].append({
            'id': item_id,
            'name': item_data["name"],
            'price': item_data["price"],
            'quantity': item_data["quantity"]
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=request.user.email if request.user.is_authenticated else None,
            success_url=request.build_absolute_uri(
                reverse('orders:success')),
            cancel_url=request.build_absolute_uri(reverse('orders:cart')),
            metadata={
                'user_id': request.user.id if request.user.is_authenticated else None,
                # Convert to string for metadata
                'cart_items': str(metadata['cart_items'])
            }
        )

        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(
            request, f"Error creating checkout session: {str(e)}")
        return redirect('orders:cart')


@csrf_exempt  # Stripe isn't a browser, so skip CSRF protection
def stripe_webhook(request):
    with open('webhook_log.txt', 'a') as f:
        f.write(f"\n\n--- Webhook received at {timezone.now()} ---\n")
        f.write(f"Headers: {request.headers}\n")
        f.write(f"Body: {request.body.decode('utf-8')[:500]}...\n")
    STRIPE_WEBHOOK = settings.STRIPE_WEBHOOK
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

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
            user_id = session.metadata.get('user_id')

            if not user_id:
                print("Missing uaer_id in session metadata")
                return HttpResponse(status=200)

            # Get service and user
            user = User.objects.get(id=user_id)

            try:
                import ast
                cart_items_str = session.metadata.get('cart_items', '[]')
                cart_items = ast.literal_eval(cart_items_str)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing cart items: {str(e)}")
                cart_items = []

            # Create an order to associate with all items
            order = Order.objects.create(
                user=user,
                is_paid=True,
                created_at=timezone.now()
            )

            # Process each cart item
            for item_data in cart_items:
                try:
                    # Get item details
                    service_id = item_data.get('id')
                    quantity = int(item_data.get('quantity', 1))

                    # Get service
                    service = Service.objects.get(id=service_id)

                    # Generate vouchers - one per quantity
                    for i in range(quantity):

                        order_item = OrderItem.objects.create(
                            order=order,
                            service=service,
                            quantity=quantity,
                            price=float(item_data.get('price', service.price))
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

                        img = qr.make_image(
                            fill_color="black", back_color="white")
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
                        print(
                            f"Voucher created: {voucher_code} for service {service.name}")

                except Service.DoesNotExist:
                    print(f"Service with id {service_id} not found")
                    continue
                except Exception as e:
                    print(f"Error processing cart item: {str(e)}")
                    continue

            print(f"Order completed and paid: {order.id}")

        except User.DoesNotExist:
            print(f"User with id {user_id} not found")
            return HttpResponse(status=200)  # Don't retry
        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return HttpResponse(status=200)  # Don't retry

    return HttpResponse(status=200)


def generate_qr_code(voucher):
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile

    # Generate QR code with voucher data
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"VOUCHER:{voucher.code}")
    qr.make(fit=True)

    # Create image from QR code
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # Save to voucher
    voucher.qr_code.save(
        f"voucher_{voucher.code}.png", ContentFile(buffer.getvalue()))


def success_view(request):
    # Verify session data or URL parameters for the Stripe session ID
    session_id = request.GET.get(
        'session_id')
    try:
        if session_id:
            # Retrieve the Stripe session to verify payment
            stripe_session = stripe.checkout.Session.retrieve(session_id)

        # Get user ID from metadata
        user_id = stripe_session.metadata.get('user_id')

        if user_id and stripe_session.payment_status == 'paid':
            user = User.objects.get(id=user_id)

            # Parse cart items from metadata
            cart_items_str = stripe_session.metadata.get('cart_items', '[]')
            cart_items = ast.literal_eval(cart_items_str)

            # Create order
            order = Order.objects.create(
                user=user,
                is_paid=True,
                created_at=timezone.now()
            )

            # Create order items and vouchers
            for item_data in cart_items:
                service_id = item_data.get('id')
                quantity = int(item_data.get('quantity', 1))
                service = Service.objects.get(id=service_id)

                # Create order item
                order_item = OrderItem.objects.create(
                    order=order,
                    service=service,
                    quantity=quantity,
                    price=float(item_data.get('price', service.price))
                )

                # Generate vouchers (one per quantity)
                for i in range(quantity):
                    # Generate unique code
                    voucher_code = str(uuid.uuid4())[:16]

                    # Create voucher
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

                    # Save QR code to voucher
                    voucher.qr_img_path.save(
                        f"voucher_qr_{voucher_code}.png",
                        ContentFile(buffer.getvalue()),
                        save=False
                    )

                    # Save voucher
                    voucher.save()

            # Clear cart
            if 'cart' in request.session:
                del request.session['cart']
                request.session.modified = True

            return render(request, 'orders/success.html', {
                'order': order,
                'vouchers': Voucher.objects.filter(order_item__order=order)
            })

    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        return render(request, 'orders/success.html')


def cancel_view(request):
    """Display page when checkout is canceled"""
    return render(request, 'orders/cancel.html')


def voucher_invoice(request, code):

    try:
        voucher = Voucher.objects.get(code=code)
        if request.user != voucher.user and not request.user.is_staff:
            return redirect('orders:my_wallet')
    except Voucher.DoesNotExist:
        return render(request, 'orders/vouc_not_found.html', {'code': code})

    context = {
        'voucher': voucher,
        'user': voucher.user,
        'service': voucher.service,

    }

    return render(request, 'voucher/invoice.html', context)


def voucher_detail(request, code):
    """Display detailed information for a single voucher"""
    voucher = get_object_or_404(Voucher, code=code, user=request.user)

    context = {
        'voucher': voucher,
        'page_title': f'Voucher: {voucher.code}',
    }

    return render(request, 'orders/voucher_detail.html', context)


@login_required
def my_wallet(request):
    """Display all of a user's vouchers in their wallet"""

    # Get active (issued) vouchers
    active_vouchers = Voucher.objects.filter(
        user=request.user,
        status="ISSUED"
    ).order_by('-issued_at')

    # Get redeemed vouchers
    redeemed_vouchers = Voucher.objects.filter(
        user=request.user,
        status="REDEEMED"
    ).order_by('-redeemed_at')

    # Get expired vouchers
    expired_vouchers = Voucher.objects.filter(
        user=request.user,
        status="EXPIRED"
    ).order_by('-expires_at')

    context = {
        'active_vouchers': active_vouchers,
        'redeemed_vouchers': redeemed_vouchers,
        'expired_vouchers': expired_vouchers,
        'page_title': 'My Wallet',
    }

    return render(request, 'orders/my_wallet.html', context)


@login_required
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

    success_message = f"Added {service.name} to your cart."
    messages.success(request, success_message)

    # Check all messages in the request
    storage = messages.get_messages(request)
    print(f"All messages: {[msg.message for msg in storage]}")
    storage.used = False  # Important: this resets the iterator so Django can use it again

    request.session.save()

    return redirect("orders:cart")


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
