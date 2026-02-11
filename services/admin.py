"""Admin registrations for services."""

from django.contrib import admin
from .models import ServiceCategory, Service, ServiceImage, Review


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    fields = ("image_url", "alt_text", "is_main", "sort_order")
    readonly_fields = ()


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active", "name")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active", "is_bundle")
    list_filter = ("is_active", "is_bundle", "category")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceImageInline]


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ("service", "is_main", "sort_order")
    list_filter = ("is_main",)
    search_fields = ("service__name",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("service", "user", "rating", "title", "created_at")
    list_filter = ("rating", "service")
    search_fields = ("service__name", "user__username", "title", "body")
