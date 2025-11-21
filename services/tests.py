from django.test import TestCase
from django.urls import reverse

from .models import ServiceCategory, Service


class ServiceListViewTests(TestCase):
    def setUp(self):
        passes = ServiceCategory.objects.create(name="Passes", slug="passes")
        packages = ServiceCategory.objects.create(name="Packages", slug="packages")
        offers = ServiceCategory.objects.create(name="Offers", slug="offers")

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
        response = self.client.get(reverse("service_list"))
        self.assertEqual(response.status_code, 200)

        # Ensure each category's service appears in the rendered page
        self.assertContains(response, "Daycare 1")
        self.assertContains(response, "Groom Pack")
        self.assertContains(response, "Special Offer")
