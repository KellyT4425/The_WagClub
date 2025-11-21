import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from services.models import ServiceCategory, Service
from .models import Order, OrderItem, Voucher

User = get_user_model()


class OrderViewsTests(TestCase):
    """
    Covers checkout/session creation, webhook order creation, and success flow.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmpdir = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.tmpdir)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="user@example.com", password="pass1234"
        )
        self.category = ServiceCategory.objects.create(
            name="Passes", slug="passes"
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Day Care",
            slug="day-care",
            description="Great care",
            price=12.34,
        )

    def test_create_checkout_session_requires_login(self):
        response = self.client.post(
            reverse("orders:create_checkout_session"), follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_redirects_to_stripe(self, mock_create):
        mock_create.return_value = SimpleNamespace(
            url="https://stripe.test/session")
        self.client.login(username="testuser", password="pass1234")

        session = self.client.session
        session["cart"] = {
            str(self.service.id): {
                "name": self.service.name,
                "price": float(self.service.price),
                "quantity": 2,
            }
        }
        session.save()

        response = self.client.post(reverse("orders:create_checkout_session"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://stripe.test/session")
        mock_create.assert_called_once()
        # Ensure metadata includes the authenticated user
        metadata = mock_create.call_args.kwargs["metadata"]
        self.assertEqual(metadata["user_id"], self.user.id)

    @patch("stripe.Webhook.construct_event")
    def test_webhook_creates_order_and_vouchers(self, mock_construct_event):
        cart_items = [
            {"id": str(self.service.id), "name": self.service.name,
             "price": "12.34", "quantity": 1}
        ]
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": SimpleNamespace(
                    metadata={"user_id": str(
                        self.user.id), "cart_items": str(cart_items)}
                )
            },
        }

        response = self.client.post(
            reverse("orders:stripe_webhook"),
            data="{}",  # body content isn't used after construct_event mock
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertTrue(order.is_paid)

        vouchers = Voucher.objects.all()
        self.assertEqual(vouchers.count(), 1)
        self.assertTrue(all(v.status == "ISSUED" for v in vouchers))
        self.assertTrue(all(v.qr_img_path.name for v in vouchers))

    @patch("stripe.checkout.Session.retrieve")
    def test_success_view_does_not_duplicate_order_creation(self, mock_retrieve):
        order = Order.objects.create(user=self.user, is_paid=True)
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="abcd1234efgh5678",
            status="ISSUED",
        )

        mock_retrieve.return_value = SimpleNamespace(
            metadata={"user_id": str(self.user.id)}, payment_status="paid"
        )
        self.client.login(username="testuser", password="pass1234")

        response = self.client.get(
            reverse("orders:success") + "?session_id=sess_123", follow=False
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)  # no duplicates
        self.assertEqual(response.context["vouchers"].count(), 1)

    def test_voucher_detail_requires_owner(self):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass1234"
        )
        order = Order.objects.create(user=self.user, is_paid=True)
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        voucher = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="owneronlycode",
            status="ISSUED",
        )

        self.client.login(username="other", password="pass1234")
        response = self.client.get(
            reverse("orders:voucher_detail", args=[voucher.code]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("orders:my_wallet"), response["Location"])
