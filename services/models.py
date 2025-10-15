from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

# Create your models here.
SERVICE_CATEGORY = [
    ("Passes", "Day Care Passes"),
    ("Packages", "Grooming Packages"),
    ("Offers", "Offers")
]


class ServiceCategory(models.Model):
    name = models.CharField(
        max_length=30, choices=SERVICE_CATEGORY, help_text="Select a Category")
    slug = models.SlugField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        """
        Meta options define model-level behavior.
        - 'verbose_name_plural' sets how this model name appears in the Django admin.
        """
        verbose_name_plural = "Service Categories"

    def __str__(self):
        """
        Returns a readable string showing the service category name.
        Used by Django admin and shell to identify each service easily.
        """
        return f"{self.name}"


class Service(models.Model):
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL, null=True, related_name="services")
    name = models.CharField(max_length=30)
    slug = models.SlugField(max_length=30, unique=True)
    img_path = models.ImageField(upload_to="services/", blank=True, null=True)
    alt_text = models.TextField(max_length=80, blank=True)
    description = models.TextField(max_length=200)
    duration_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00, help_text="Duration (hours)", blank=True, null=True)
    price = models.DecimalField(max_digits=4, decimal_places=2)
    is_bundle = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        """
        Meta options define model-level behavior.
        - 'verbose_name_plural' sets how this model name appears in the Django admin.
        """
        verbose_name_plural = "Services"

    def __str__(self):
        """
        Returns a readable string showing the service name and price.
        Used by Django admin and shell to identify each service easily.
        """
        return f"{self.name} (€{self.price})"


class ServiceImage(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="images")
    image_url = models.ImageField(
        upload_to="services/", blank=False, null=False)
    alt_text = models.TextField(max_length=120, blank=True)
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        """
        Meta options define model-level behavior:
        - 'ordering' sorts images by sort_order then id when retrieved.
        - 'constraints' ensures each service can only have one main image.
        - 'verbose_name_plural' changes how the model name appears in admin.
        """
        ordering = ["sort_order", "id"]
        verbose_name_plural = "Service Images"
        constraints = [
            models.UniqueConstraint(
                fields=["service"],
                condition=Q(is_main=True),
                name="unique_main_image_per_service",
            )
        ]

    def clean(self):
        """
        Ensures that each service has only one main image.
        If this image is marked as main, the method checks the database
        for any other image linked to the same service that is also main.
        If another main image exists, a ValidationError is raised.
        """
        if self.is_main and self.service_id:
            qs = ServiceImage.objects.filter(
                service=self.service, is_main=True)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                "Only one main image is allowed per service.")
