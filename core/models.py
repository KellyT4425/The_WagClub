from django.db import models


class NewsletterSignup(models.Model):
    """Stores newsletter subscribers."""

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email
