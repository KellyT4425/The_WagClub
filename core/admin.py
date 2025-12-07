import logging

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import NewsletterSignup

logger = logging.getLogger(__name__)
User = get_user_model()


class LoggingUserAdmin(DjangoUserAdmin):
    """Custom User admin that logs exceptions on delete_view for debugging."""

    def delete_view(self, request, object_id, extra_context=None):
        try:
            return super().delete_view(request, object_id, extra_context)
        except Exception:
            logger.exception("Error deleting user via admin",
                             extra={"user_id": object_id})
            raise


admin.site.unregister(User)
admin.site.register(User, LoggingUserAdmin)


@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at",)
