from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from orders.models import Order, OrderItem, Voucher
from .models import ServiceCategory, Service, Review


class ServiceListViewTests(TestCase):
    def setUp(self):
        passes = ServiceCategory.objects.create(name="Passes", slug="passes")
        packages = ServiceCategory.objects.create(
            name="Packages", slug="packages"
        )
        offers = ServiceCategory.objects.create(
            name="Offers", slug="offers"
        )

        Service.objects.create(
            category=passes,
            name="Daycare 1",
            slug="daycare-1",
            description="A",
            price=10,
        )
        Service.objects.create(
            category=packages,
            name="Groom Pack",
            slug="groom-pack",
            description="B",
            price=20,
        )
        Service.objects.create(
            category=offers,
            name="Special Offer",
            slug="special-offer",
            description="C",
            price=5,
        )

    def test_service_list_displays_by_category_names(self):
        response = self.client.get(reverse("services:service_list"))
        self.assertEqual(response.status_code, 200)

        # Ensure each category's service appears in the rendered page
        self.assertContains(response, "Daycare 1")
        self.assertContains(response, "Groom Pack")
        self.assertContains(response, "Special Offer")

    def test_service_search_filters_results(self):
        response = self.client.get(
            reverse("services:service_list"), {"q": "groom"}
        )
        self.assertEqual(response.status_code, 200)
        # Context search_results should only include the matching service
        results = response.context["search_results"]
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().name, "Groom Pack")

    def test_service_search_no_results_shows_message(self):
        response = self.client.get(
            reverse("services:service_list"), {"q": "cat"}
        )
        self.assertEqual(response.status_code, 200)
        results = response.context["search_results"]
        self.assertEqual(results.count(), 0)
        self.assertContains(response, "Try a different keyword")


class ReviewCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="reviewer", email="reviewer@example.com", password="pass12345"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass12345"
        )
        self.category = ServiceCategory.objects.create(
            name="Passes", slug="passes"
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Daycare 1",
            slug="daycare-1",
            description="A",
            price=10,
        )

    def _create_voucher_for_user(self, user):
        order = Order.objects.create(user=user, is_paid=True)
        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=10
        )
        return Voucher.objects.create(
            service=self.service,
            order_item=order_item,
            user=user,
            code=f"CODE{user.id}",
            status="ISSUED",
        )

    def test_review_create_requires_login(self):
        url = reverse("services:service_detail", args=[self.service.slug])
        response = self.client.post(
            url, {"rating": 5, "title": "Great", "body": "A" * 25}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_create_requires_voucher(self):
        self.client.login(username="reviewer", password="pass12345")
        url = reverse("services:service_detail", args=[self.service.slug])
        response = self.client.post(
            url, {"rating": 5, "title": "Great", "body": "A" * 25}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_create_success_with_voucher(self):
        self._create_voucher_for_user(self.user)
        self.client.login(username="reviewer", password="pass12345")
        url = reverse("services:service_detail", args=[self.service.slug])
        response = self.client.post(
            url, {"rating": 5, "title": "Great", "body": "A" * 25}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        review = Review.objects.first()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.service, self.service)

    def test_review_validation_blocks_bad_rating(self):
        self._create_voucher_for_user(self.user)
        self.client.login(username="reviewer", password="pass12345")
        url = reverse("services:service_detail", args=[self.service.slug])
        response = self.client.post(
            url, {"rating": 6, "title": "Bad", "body": "A" * 25}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rating must be between 1 and 5")
        self.assertEqual(Review.objects.count(), 0)

    def test_review_validation_blocks_short_body(self):
        self._create_voucher_for_user(self.user)
        self.client.login(username="reviewer", password="pass12345")
        url = reverse("services:service_detail", args=[self.service.slug])
        response = self.client.post(
            url, {"rating": 5, "title": "Bad", "body": "Too short"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review must be at least 20 characters.")
        self.assertEqual(Review.objects.count(), 0)

    def test_review_edit_author_only(self):
        self._create_voucher_for_user(self.user)
        review = Review.objects.create(
            service=self.service,
            user=self.user,
            rating=5,
            title="Great",
            body="A" * 25,
        )
        self.client.login(username="other", password="pass12345")
        url = reverse("services:review_edit", args=[review.pk])
        response = self.client.post(
            url, {"rating": 4, "title": "Edit", "body": "B" * 25}
        )
        self.assertEqual(response.status_code, 403)

    def test_review_delete_author_only(self):
        self._create_voucher_for_user(self.user)
        review = Review.objects.create(
            service=self.service,
            user=self.user,
            rating=5,
            title="Great",
            body="A" * 25,
        )
        self.client.login(username="other", password="pass12345")
        url = reverse("services:review_delete", args=[review.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
