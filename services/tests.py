from django.test import TestCase
from django.urls import reverse

from .models import ServiceCategory, Service


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
