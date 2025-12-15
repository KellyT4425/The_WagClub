"""Admin registrations for orders."""

from django.contrib import admin
from .models import Order, OrderItem, Voucher


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("service", "quantity", "price")
    readonly_fields = ()


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_paid", "created_at")
    list_filter = ("is_paid", "created_at")
    search_fields = ("user__email", "user__username", "items__service__name")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)


@admin.action(description="Mark selected vouchers as redeemed")
def mark_as_redeemed(modeladmin, request, queryset):
    queryset.update(status="REDEEMED")


@admin.action(description="Mark selected vouchers as expired")
def mark_as_expired(modeladmin, request, queryset):
    queryset.update(status="EXPIRED")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "user",
        "service",
        "status",
        "issued_at",
        "expires_at",
    )
    list_filter = ("status", "issued_at", "expires_at", "service")
    search_fields = ("code", "user__email", "user__username", "service__name")
    readonly_fields = ("issued_at", "redeemed_at")
    actions = [mark_as_redeemed, mark_as_expired]


admin.site.site_header = "The Wag Club Admin"
admin.site.index_title = "Administration"
admin.site.site_title = "The Wag Club Admin"
