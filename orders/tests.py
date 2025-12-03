import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

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
        session_id = "sess_123"
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": SimpleNamespace(
                    id=session_id,
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
        self.assertEqual(order.stripe_session_id, session_id)
        self.assertTrue(order.is_paid)

        vouchers = Voucher.objects.all()
        self.assertEqual(vouchers.count(), 1)
        self.assertTrue(all(v.status == "ISSUED" for v in vouchers))
        self.assertTrue(all(v.qr_img_path.name for v in vouchers))

    @patch("stripe.Webhook.construct_event")
    def test_webhook_is_idempotent(self, mock_construct_event):
        cart_items = [
            {"id": str(self.service.id), "name": self.service.name,
             "price": "12.34", "quantity": 1}
        ]
        session_id = "sess_dupe"
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": SimpleNamespace(
                    id=session_id,
                    metadata={"user_id": str(
                        self.user.id), "cart_items": str(cart_items)}
                )
            },
        }

        for _ in range(2):
            response = self.client.post(
                reverse("orders:stripe_webhook"),
                data="{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Voucher.objects.count(), 1)
        self.assertEqual(
            Order.objects.first().stripe_session_id, session_id
        )

    @patch("stripe.checkout.Session.retrieve")
    def test_success_view_does_not_duplicate_order_creation(self, mock_retrieve):
        session_id = "sess_123"
        order = Order.objects.create(
            user=self.user, is_paid=True, stripe_session_id=session_id
        )
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
            id=session_id,
            metadata={"user_id": str(self.user.id)},
            payment_status="paid",
        )
        self.client.login(username="testuser", password="pass1234")

        response = self.client.get(
            reverse("orders:success") + f"?session_id={session_id}", follow=False
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)  # no duplicates
        self.assertEqual(response.context["vouchers"].count(), 1)

    @patch("stripe.checkout.Session.retrieve")
    def test_success_view_allows_unauthenticated_with_metadata(self, mock_retrieve):
        session_id = "sess_unauth"
        order = Order.objects.create(
            user=self.user, is_paid=True, stripe_session_id=session_id
        )
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="unauthcode",
            status="ISSUED",
        )

        mock_retrieve.return_value = SimpleNamespace(
            id=session_id,
            metadata={"user_id": str(self.user.id)},
            payment_status="paid",
        )

        response = self.client.get(
            reverse("orders:success") + f"?session_id={session_id}", follow=False
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "unauthcode")

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

    def test_voucher_invoice_requires_login(self):
        order = Order.objects.create(
            user=self.user, is_paid=True, stripe_session_id="sess_invoice_1"
        )
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        voucher = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="invoicecode",
            status="ISSUED",
        )

        response = self.client.get(
            reverse("orders:voucher_invoice", args=[voucher.code]), follow=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_voucher_invoice_404_for_non_owner(self):
        other_user = User.objects.create_user(
            username="other2", email="other2@example.com", password="pass1234"
        )
        order = Order.objects.create(
            user=self.user, is_paid=True, stripe_session_id="sess_invoice_2"
        )
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        voucher = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="invoicecode2",
            status="ISSUED",
        )

        self.client.login(username="other2", password="pass1234")
        response = self.client.get(
            reverse("orders:voucher_invoice", args=[voucher.code]), follow=False
        )

        self.assertEqual(response.status_code, 404)

    def test_my_wallet_groups_vouchers_by_status(self):
        order = Order.objects.create(user=self.user, is_paid=True)
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        issued = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="issuedcode",
            status="ISSUED",
        )
        redeemed = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="redeemedcode",
            status="REDEEMED",
            redeemed_at=timezone.now(),
        )
        expired = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="expiredcode",
            status="EXPIRED",
            expires_at=timezone.now(),
        )

        self.client.login(username="testuser", password="pass1234")
        response = self.client.get(reverse("orders:my_wallet"))
        self.assertEqual(response.status_code, 200)
        # Active section shows issued
        self.assertContains(response, issued.code)
        # Redeemed/expired sections show their codes
        self.assertContains(response, redeemed.code)
        self.assertContains(response, expired.code)

    def test_scan_voucher_redeem_requires_staff(self):
        order = Order.objects.create(user=self.user, is_paid=True)
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=self.service.price
        )
        voucher = Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=self.user,
            code="scanme",
            status="ISSUED",
        )

        # Non-staff cannot redeem
        self.client.login(username="testuser", password="pass1234")
        response = self.client.post(reverse("orders:scan_voucher", args=[voucher.code]))
        voucher.refresh_from_db()
        self.assertEqual(voucher.status, "ISSUED")
        self.assertEqual(response.status_code, 302)

        # Staff can redeem
        staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass1234", is_staff=True
        )
        self.client.login(username="staff", password="pass1234")
        response = self.client.post(reverse("orders:scan_voucher", args=[voucher.code]))
        voucher.refresh_from_db()
        self.assertEqual(voucher.status, "REDEEMED")
        self.assertEqual(response.status_code, 302)
