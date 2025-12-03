from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from services.models import Service
from .models import Voucher, Order, OrderItem
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
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


def staff_required(user):
    return user.is_staff or user.is_superuser


@login_required
def create_checkout_session(request):
    """Create a Stripe Checkout session from the current cart."""
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
                "product_data": {
                    "name": item_data["name"],
                    "metadata": {
                        "service_id": item_id,
                        "user_id": str(request.user.id)
                    }
                },
                "unit_amount": price_cents,  # Amount in cents
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
                reverse('orders:success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('orders:cart')),
            metadata={
                'user_id': request.user.id if request.user.is_authenticated else None,
                # Convert to string for metadata
                'cart_items': str(metadata['cart_items'])
            }
        )

        return redirect(checkout_session.url, code=303)
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # DEBUG LOGGING
        messages.error(
            request, f"Error creating checkout session: {str(e)}")
        return redirect('orders:cart')


@csrf_exempt  # Stripe isn't a browser, so skip CSRF protection
def stripe_webhook(request):
    """Handle Stripe webhook events and create orders/vouchers on payment success."""
    import logging
    logger = logging.getLogger('stripe')
    # LOG INCOMING PAYLOAD
    logger.info(f"Webhook received: {request.body.decode('utf-8')}")

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
        session_id = getattr(session, "id", None)
        if session_id is None and isinstance(session, dict):
            session_id = session.get("id")

        metadata = getattr(session, "metadata", None)
        if metadata is None and isinstance(session, dict):
            metadata = session.get("metadata")

        try:
            # Extract metadata
            if metadata is None:
                print("Missing metadata in session")
                return HttpResponse(status=200)

            user_id = metadata.get('user_id')

            if not user_id:
                print("Missing user_id in session metadata")
                return HttpResponse(status=200)

            if session_id and Order.objects.filter(stripe_session_id=session_id).exists():
                print(f"Order already processed for session {session_id}")
                return HttpResponse(status=200)

            # Get service and user
            user = User.objects.get(id=user_id)

            try:
                cart_items_str = metadata.get('cart_items', '[]')
                cart_items = ast.literal_eval(cart_items_str)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing cart items: {str(e)}")
                cart_items = []

            # Create an order to associate with all items
            order = Order.objects.create(
                user=user,
                is_paid=True,
                created_at=timezone.now(),
                stripe_session_id=session_id,
            )

            # Process each cart item
            for item_data in cart_items:
                try:
                    # Get item details
                    service_id = item_data.get('id')
                    total_quantity = int(item_data.get('quantity', 1))

                    # Get service
                    service = Service.objects.get(id=service_id)
                    price = float(item_data.get('price', service.price))

                    order_item = OrderItem.objects.create(
                        order=order,
                        service=service,
                        quantity=total_quantity,
                        price=price
                    )

                    # Generate vouchers - one per quantity
                    for i in range(total_quantity):
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

                        generate_qr_code(voucher)
                        voucher.save()
                        print(f"Voucher created: {voucher_code} for service {service.name}")

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


def generate_qr_code(voucher, site_url=None):
    """Generate and attach a QR image for a voucher that points to scan/redeem."""
    site_root = site_url or getattr(settings, "SITE_URL", "")
    site_root = (site_root or "http://localhost:8000").rstrip("/")
    scan_path = reverse("orders:scan_voucher", args=[voucher.code])
    scan_url = f"{site_root}{scan_path}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(scan_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    voucher.qr_img_path.save(
        f"voucher_qr_{voucher.code}.png", ContentFile(buffer.getvalue()), save=False
    )


@login_required
def success_view(request):
    """Show the success page; orders/vouchers are created via webhook."""
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, "Missing Stripe session; please try again or contact support.")
        return redirect('orders:cart')

    try:
        stripe_session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        messages.error(request, "Unable to verify payment with Stripe.")
        return redirect('orders:cart')

    metadata = getattr(stripe_session, "metadata", None)
    if metadata is None and isinstance(stripe_session, dict):
        metadata = stripe_session.get("metadata")

    user_id = metadata.get('user_id') if metadata else None
    if str(user_id) != str(request.user.id):
        messages.error(request, "This payment does not belong to your account.")
        return redirect('orders:cart')

    payment_status = getattr(stripe_session, "payment_status", None)
    if payment_status is None and isinstance(stripe_session, dict):
        payment_status = stripe_session.get("payment_status")

    if payment_status != 'paid':
        messages.warning(request, "Payment not completed. You have not been charged.")
        return redirect('orders:cart')

    order = Order.objects.filter(
        user=request.user, is_paid=True, stripe_session_id=session_id
    ).order_by('-created_at').first()

    if not order:
        messages.warning(
            request,
            "We couldn't find your order for this payment yet. "
            "Please check again in a moment or contact support.",
        )
        return redirect('orders:cart')

    vouchers = Voucher.objects.filter(order_item__order=order)

    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True

    return render(request, 'orders/success.html', {
        'order': order,
        'vouchers': vouchers,
    })


def cancel_view(request):
    """Display page when checkout is canceled."""
    return render(request, 'orders/cancel.html')


@login_required
def voucher_invoice(request, code):
    """Render an invoice for a voucher owned by the current user."""
    try:
        voucher = Voucher.objects.get(code=code, user=request.user)
    except Voucher.DoesNotExist:
        return render(
            request, 'orders/vouc_not_found.html', {'code': code}, status=404
        )

    context = {
        'voucher': voucher,
        'user': voucher.user,
        'service': voucher.service,

    }

    return render(request, 'orders/invoice.html', context)


@login_required
def voucher_detail(request, code):
    """Display detailed information for a single voucher."""
    voucher = get_object_or_404(Voucher, code=code)

    # Only the voucher owner OR staff/superuser can view it
    if request.user != voucher.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request, "You do not have permission to view this voucher.")
        return redirect("orders:my_wallet")

    context = {
        'voucher': voucher,
        'page_title': f'Voucher: {voucher.code}',
        "MEDIA_URL": settings.MEDIA_URL,
    }

    return render(request, 'orders/voucher_detail.html', context)


@login_required
@user_passes_test(staff_required)
def redeem_voucher(request, code):
    """Allow staff/admin to redeem an ISSUED voucher."""
    voucher = get_object_or_404(Voucher, code=code)

    if request.method != "POST":
        messages.error(
            request, "Voucher can only be redeemed with a POST request.")
        return redirect("orders:voucher_detail", code=code)

    if voucher.status != "ISSUED":
        messages.warning(
            request, "This voucher cannot be redeemed (already used or expired).")
        return redirect("orders:voucher_detail", code=code)

    # Mark as redeemed
    voucher.status = "REDEEMED"
    voucher.redeemed_at = timezone.now()
    voucher.save()

    messages.success(request, f"Voucher {voucher.code} has been redeemed.")
    return redirect("orders:voucher_detail", code=code)


@login_required
def scan_voucher(request, code):
    """Staff-facing scan/verify view. Staff can redeem; others only view status."""
    voucher = get_object_or_404(Voucher, code=code)

    if request.method == "POST":
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "You do not have permission to redeem vouchers.")
            return redirect("orders:scan_voucher", code=code)

        if voucher.status != "ISSUED":
            messages.warning(
                request, "This voucher cannot be redeemed (already used or expired)."
            )
            return redirect("orders:scan_voucher", code=code)

        voucher.status = "REDEEMED"
        voucher.redeemed_at = timezone.now()
        voucher.save()
        messages.success(request, f"Voucher {voucher.code} has been redeemed.")
        return redirect("orders:scan_voucher", code=code)

    context = {
        "voucher": voucher,
        "can_redeem": request.user.is_staff or request.user.is_superuser,
    }
    return render(request, "orders/scan_voucher.html", context)


@login_required
def my_wallet(request):
    """Display all of a user's vouchers grouped by status."""

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
        "MEDIA_URL": settings.MEDIA_URL,
    }

    return render(request, "orders/my_wallet.html", context)


@login_required
def add_to_cart(request):
    """Add a service to the session cart."""
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
    """Remove an item from the session cart."""
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
    """Display the current session cart."""
    cart = request.session.get(
        "cart", {})
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
