from django.shortcuts import render, redirect
from .models import Voucher, Order, Service
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe
import uuid
import qrcode
from io import BytesIO
from django.urls import reverse
from django.conf import settings

stripe.api_key = settings.STRIPE_RESTRICTED_KEY


def create_checkout_session(request, service_id):
    """Create a Stripe Checkout Session for a specific service"""
    try:
        # Get the service from the database
        service = Service.objects.get(id=service_id, is_active=True)

        # Create a checkout session with the service details
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',  # Adjust currency as needed
                        'product_data': {
                            'name': service.name,
                            'description': service.description,
                            # You can add an image if available
                            'images': [request.build_absolute_uri(service.img_path.url)] if service.img_path else [],
                        },
                        # Convert decimal to cents
                        'unit_amount': int(service.price * 100),
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.build_absolute_uri(
                reverse('checkout_success')),
            cancel_url=request.build_absolute_uri(reverse('checkout_cancel')),
            metadata={
                'service_id': service.id,
                # You can add user_id if the user is authenticated
                'user_id': request.user.id if request.user.is_authenticated else None,
            },
        )
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            service=service,
            amount=service.price,
            stripe_session_id=checkout_session.id,
            # Add other fields as needed
        )

        return redirect(checkout_session.url)
    except Service.DoesNotExist:
        return render(request, 'orders/error.html', {'error': 'Service not found'})
    except Exception as e:
        return render(request, 'orders/error.html', {'error': str(e)})


@csrf_exempt  # Stripe isn't a browser, so skip CSRF protection
def stripe_webhook(request):
    webhook_secret = settings.STRIPE_WEBHOOK
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
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
            # Find the order associated with this checkout session
            order = Order.objects.get(stripe_session_id=session.id)

            # Mark the order as paid
            order.is_paid = True
            order.save()

            # Generate a unique voucher code
            import random
            import string
            code = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=8))

            # Create a voucher
            voucher = Voucher.objects.create(
                code=code,
                order=order,
                service=order.service,
                user=order.user,
                # Add other voucher fields as needed
            )

            # Send an email with the voucher details (implement this)
            # send_voucher_email(order.user.email, voucher)

            print(f"Payment completed! Voucher created: {code}")

        except Order.DoesNotExist:
            print(f"Order not found for session ID: {session.id}")

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
    # 👉 This is where you'd mark the order as paid,
    # generate a voucher, send email, etc.
    print("Payment successful for session:", session.id)

    return HttpResponse(status=200)


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


def cart(request):

    return render(request, 'orders/cart.html')
