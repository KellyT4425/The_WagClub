"""Order and voucher views: checkout, webhooks, wallet, QR, redemption."""

import ast
import hashlib
from io import BytesIO
import uuid

import qrcode
import stripe
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from services.models import Service

from .models import Order, OrderItem, Voucher

try:  # Cloudinary upload (optional)
    import cloudinary.uploader as cloud_uploader
except Exception:  # pragma: no cover
    cloud_uploader = None

# Stripe exceptions can live in different modules across versions
try:
    from stripe.error import SignatureVerificationError
except Exception:  # pragma: no cover - fallback for newer packages
    try:
        from stripe._error import SignatureVerificationError  # type: ignore
    except Exception:  # pragma: no cover
        SignatureVerificationError = None

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


def staff_required(user):
    """Return True if user is staff or superuser."""
    return user.is_staff or user.is_superuser


def get_site_root(request):
    """Return SITE_URL or derive from request."""
    site_root = getattr(settings, "SITE_URL", "") or ""
    site_root = site_root.rstrip("/")
    if not site_root:
        site_root = request.build_absolute_uri("/").rstrip("/")
    return site_root


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
    metadata = {"cart_items": []}

    for item_id, item_data in cart.items():
        price_cents = int(Decimal(str(item_data["price"])) * 100)
        line_items.append(
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": item_data["name"],
                        "metadata": {
                            "service_id": item_id,
                            "user_id": str(request.user.id),
                        },
                    },
                    "unit_amount": price_cents,  # Amount in cents
                },
                "quantity": item_data["quantity"],
            }
        )

        metadata["cart_items"].append(
            {
                "id": item_id,
                "name": item_data["name"],
                "price": item_data["price"],
                "quantity": item_data["quantity"],
            }
        )

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            customer_email=(
                request.user.email if request.user.is_authenticated else None
            ),
            success_url=(
                request.build_absolute_uri(reverse("orders:success"))
                + "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=request.build_absolute_uri(reverse("orders:cart")),
            metadata={
                "user_id": (
                    request.user.id if request.user.is_authenticated else None
                ),
                "cart_items": str(metadata["cart_items"]),
            },
        )

        return redirect(checkout_session.url, code=303)
    except Exception as e:
        import traceback

        print(traceback.format_exc())  # DEBUG LOGGING
        messages.error(request, f"Error creating checkout session: {str(e)}")
        return redirect("orders:cart")


@csrf_exempt  # Stripe isn't a browser, so skip CSRF protection
def stripe_webhook(request):
    """
    Handle Stripe webhook events and create orders/vouchers on payment
    success.
    """
    import logging
    logger = logging.getLogger("stripe")
    # LOG INCOMING PAYLOAD
    logger.info(f"Webhook received: {request.body.decode('utf-8')}")

    STRIPE_WEBHOOK = settings.STRIPE_WEBHOOK
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except Exception as exc:
        # Handle signature errors across stripe versions without breaking on
        # AttributeError
        if SignatureVerificationError and isinstance(
            exc, SignatureVerificationError
        ):
            return HttpResponse(status=400)
        raise

    # Handle the event types you care about:
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
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

            user_id = metadata.get("user_id")

            if not user_id:
                print("Missing user_id in session metadata")
                return HttpResponse(status=200)

            if session_id and Order.objects.filter(
                stripe_session_id=session_id
            ).exists():
                print(f"Order already processed for session {session_id}")
                return HttpResponse(status=200)

            # Get service and user
            user = User.objects.get(id=user_id)

            try:
                cart_items_str = metadata.get("cart_items", "[]")
                cart_items = ast.literal_eval(cart_items_str)
            except (ValueError, SyntaxError) as e:
                print(f"Error parsing cart items: {str(e)}")
                cart_items = []

            # Create an order to associate with all items
            try:
                order = Order.objects.create(
                    user=user,
                    is_paid=True,
                    created_at=timezone.now(),
                    stripe_session_id=session_id,
                )
            except IntegrityError:
                # Another process already created this order for this session
                existing_order = Order.objects.filter(
                    stripe_session_id=session_id
                ).first()
                if existing_order:
                    print(f"Order already exists for session {session_id}")
                    return HttpResponse(status=200)
                raise

            # Process each cart item
            for item_data in cart_items:
                try:
                    # Get item details
                    service_id = item_data.get("id")
                    total_quantity = int(item_data.get("quantity", 1))

                    # Get service
                    service = Service.objects.get(id=service_id)
                    price = float(item_data.get("price", service.price))

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
                            status="ISSUED",
                        )

                        generate_qr_code(voucher)
                        voucher.save()
                        print(
                            "Voucher created: "
                            f"{voucher_code} for service {service.name}"
                        )

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
    """Generate and attach a QR image pointing to the staff redemption page."""
    site_root = site_url or getattr(settings, "SITE_URL", "")
    site_root = (site_root or "http://localhost:8000").rstrip("/")
    redeem_path = reverse("orders:scan_voucher", args=[voucher.code])
    redeem_url = f"{site_root}{redeem_path}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(redeem_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    filename = f"vouchers/qr_codes/{voucher.code}.png"
    try:
        exists = default_storage.exists(filename)
    except Exception:
        exists = False

    if not exists:
        try:
            default_storage.save(filename, ContentFile(buffer.getvalue()))
        except Exception:
            # Keep voucher generation resilient if storage is unavailable.
            pass
    voucher.qr_img_path.name = filename


def qr_redirect(request):
    """
    Deterministic QR generator backed by Cloudinary/default storage.
    Expects ?t=<text>; uses sha1(text) for public_id to allow CDN reuse.
    """
    text = (request.GET.get("t") or "").strip()
    if not text:
        return HttpResponseBadRequest("Missing t")

    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    public_id = f"qr/{digest}"
    filename = f"{public_id}.png"

    # If already present, redirect immediately
    try:
        if default_storage.exists(filename):
            return redirect(default_storage.url(filename))
    except Exception:
        pass

    # Generate QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # Prefer Cloudinary upload when available
    if cloud_uploader:
        try:
            res = cloud_uploader.upload(
                buffer.getvalue(),
                public_id=public_id,
                overwrite=True,
                unique_filename=False,
                resource_type="image",
                format="png",
            )
            url = res.get("secure_url") or res.get("url")
            if url:
                return redirect(url)
        except Exception:
            pass

    # Fallback to default storage
    try:
        if default_storage.exists(filename):
            default_storage.delete(filename)
        default_storage.save(filename, ContentFile(buffer.getvalue()))
        return redirect(default_storage.url(filename))
    except Exception:
        return HttpResponse(status=500)


def success_view(request):
    """Show the success page; orders/vouchers are created via webhook."""
    session_id = request.GET.get("session_id")
    if not session_id:
        messages.error(
            request,
            "Missing Stripe session; please try again or contact support.",
        )
        return redirect("orders:cart")

    try:
        stripe_session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        messages.error(request, "Unable to verify payment with Stripe.")
        return redirect("orders:cart")

    metadata = getattr(stripe_session, "metadata", None)
    if metadata is None and isinstance(stripe_session, dict):
        metadata = stripe_session.get("metadata")

    user_id = metadata.get("user_id") if metadata else None
    if not user_id:
        messages.error(
            request, "Missing payment metadata; please contact support."
        )
        return redirect("orders:cart")

    try:
        order_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(
            request, "We could not verify the account for this payment."
        )
        return redirect("orders:cart")

    if request.user.is_authenticated and str(request.user.id) != str(user_id):
        messages.error(
            request, "This payment does not belong to your account."
        )
        return redirect("orders:cart")

    payment_status = getattr(stripe_session, "payment_status", None)
    if payment_status is None and isinstance(stripe_session, dict):
        payment_status = stripe_session.get("payment_status")

    if payment_status != "paid":
        messages.warning(
            request, "Payment not completed. You have not been charged."
        )
        return redirect("orders:cart")

    order = Order.objects.filter(
        user=order_user, is_paid=True, stripe_session_id=session_id
    ).order_by("-created_at").first()

    pending = False
    vouchers = []

    if not order:
        pending = True
        try:
            order = build_order_from_session(
                order_user, stripe_session, metadata, session_id
            )
            if order:
                vouchers = Voucher.objects.filter(order_item__order=order)
                pending = False
        except Exception:
            pending = True
    else:
        vouchers = Voucher.objects.filter(order_item__order=order)

    if not pending and "cart" in request.session:
        del request.session["cart"]
        request.session.modified = True

    return render(
        request,
        "orders/success.html",
        {
            "order": order,
            "vouchers": vouchers,
            "site_root": get_site_root(request),
            "pending_order": pending,
            "session_id": session_id,
        },
    )


def cancel_view(request):
    """Display page when checkout is canceled."""
    return render(request, 'orders/cancel.html')


def build_order_from_session(user, stripe_session, metadata, session_id):
    """
    Fallback: create order/vouchers from the Stripe session metadata when
    webhook hasn't completed yet. Returns the order or None.
    """
    if metadata is None:
        return None

    cart_items_str = metadata.get("cart_items", "[]")
    try:
        cart_items = ast.literal_eval(cart_items_str)
    except Exception:
        cart_items = []

    order, created = Order.objects.get_or_create(
        stripe_session_id=session_id,
        defaults={
            "user": user,
            "is_paid": True,
            "created_at": timezone.now(),
        },
    )

    # If order already existed, don't recreate items
    if not created:
        return order

    for item_data in cart_items:
        try:
            service_id = item_data.get("id")
            total_quantity = int(item_data.get("quantity", 1))
            service = Service.objects.get(id=service_id)
            price = float(item_data.get("price", service.price))

            order_item = OrderItem.objects.create(
                order=order,
                service=service,
                quantity=total_quantity,
                price=price
            )

            for _ in range(total_quantity):
                voucher_code = str(uuid.uuid4())[:16]
                voucher = Voucher(
                    service=service,
                    order_item=order_item,
                    user=user,
                    code=voucher_code,
                    status="ISSUED"
                )
                generate_qr_code(voucher)
                voucher.save()
        except Exception:
            continue

    return order


@login_required
def voucher_invoice(request, code):
    """Render an invoice for a voucher owned by the current user."""
    try:
        voucher = Voucher.objects.get(code=code, user=request.user)
    except Voucher.DoesNotExist:
        return render(
            request,
            "orders/vouc_not_found.html",
            {"code": code},
            status=404,
        )

    context = {
        "voucher": voucher,
        "user": voucher.user,
        "service": voucher.service,
        "site_root": get_site_root(request),
    }

    return render(request, "orders/invoice.html", context)


@login_required
def voucher_detail(request, code):
    """Display detailed information for a single voucher."""
    voucher = get_object_or_404(Voucher, code=code)

    # Only the voucher owner OR staff/superuser can view it
    if (
        request.user != voucher.user
        and not request.user.is_staff
        and not request.user.is_superuser
    ):
        messages.error(
            request, "You do not have permission to view this voucher.")
        return redirect("orders:my_wallet")

    context = {
        "voucher": voucher,
        "page_title": f"Voucher: {voucher.code}",
        "MEDIA_URL": settings.MEDIA_URL,
        "site_root": get_site_root(request),
    }

    return render(request, "orders/voucher_detail.html", context)


def voucher_qr_image(request, code):
    """
    Serve voucher QR by ensuring it's stored via default storage (Cloudinary in
    prod) and redirecting to the storage URL.
    """
    voucher = get_object_or_404(Voucher, code=code)
    filename = f"vouchers/qr_codes/{voucher.code}.png"

    try:
        exists = default_storage.exists(filename)
    except Exception:
        exists = False

    if not exists:
        # Generate on-demand if missing
        generate_qr_code(voucher)
        voucher.save(update_fields=["qr_img_path"])

    url = default_storage.url(filename)
    return redirect(url)


@login_required
@user_passes_test(staff_required)
@require_http_methods(["GET", "POST"])
def redeem_voucher(request, code):
    """Staff/admin redeem flow; GET shows confirmation, POST redeems."""
    voucher = get_object_or_404(Voucher, code=code)

    if request.method == "POST":
        if voucher.status != "ISSUED":
            messages.warning(
                request,
                "This voucher cannot be redeemed (already used or expired).",
            )
            return redirect("orders:redeem_voucher", code=code)

        voucher.status = "REDEEMED"
        voucher.redeemed_at = timezone.now()
        voucher.save()
        messages.success(request, f"Voucher {voucher.code} has been redeemed.")
        return redirect("orders:redeem_voucher", code=code)

    context = {
        "voucher": voucher,
        "can_redeem": True,
        "redeem_action_url": reverse(
            "orders:redeem_voucher", args=[voucher.code]
        ),
        "default_redeem_url": reverse(
            "orders:redeem_voucher", args=[voucher.code]
        ),
        "site_root": get_site_root(request),
    }
    return render(request, "orders/scan_voucher.html", context)


@login_required
def scan_voucher(request, code):
    """
    Staff-facing scan/verify view. Staff can redeem; others only view status.
    """
    voucher = get_object_or_404(Voucher, code=code)

    if request.method == "POST":
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(
                request, "You do not have permission to redeem vouchers."
            )
            return redirect("orders:scan_voucher", code=code)

        if voucher.status != "ISSUED":
            messages.warning(
                request,
                "This voucher cannot be redeemed (already used or expired).",
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
        "default_redeem_url": reverse(
            "orders:scan_voucher", args=[voucher.code]
        ),
        "site_root": get_site_root(request),
    }
    return render(request, "orders/scan_voucher.html", context)


@login_required
def my_wallet(request):
    """Display all of a user's vouchers grouped by status."""

    active_vouchers = Voucher.objects.filter(
        user=request.user, status="ISSUED"
    ).order_by("-issued_at")

    redeemed_vouchers = Voucher.objects.filter(
        user=request.user, status="REDEEMED"
    ).order_by("-redeemed_at")

    expired_vouchers = Voucher.objects.filter(
        user=request.user, status="EXPIRED"
    ).order_by("-expires_at")

    context = {
        'active_vouchers': active_vouchers,
        'redeemed_vouchers': redeemed_vouchers,
        'expired_vouchers': expired_vouchers,
        'page_title': 'My Wallet',
        "MEDIA_URL": settings.MEDIA_URL,
        'site_root': get_site_root(request),
    }

    return render(request, "orders/my_wallet.html", context)


@login_required
def add_to_cart(request):
    """Add a service to the session cart."""
    if request.method != "POST":
        return redirect("orders:cart")

    service_id = request.POST.get("service_id")
    raw_qty = request.POST.get("quantity", 1)
    try:
        qty = int(raw_qty)
    except (TypeError, ValueError):
        messages.error(request, "Invalid quantity.")
        return redirect("orders:cart")

    if qty <= 0:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("orders:cart")

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

    # Check all messages in the request
    storage = messages.get_messages(request)
    print(f"All messages: {[msg.message for msg in storage]}")
    storage.used = False  # reset iterator so Django can use it again

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
