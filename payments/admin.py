from django.contrib import admin
from django.utils.html import format_html
from .models import GigPayment, PremiumSubscription


@admin.register(PremiumSubscription)
class PremiumSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "teacher_email",
        "amount",
        "duration_days",
        "status_badge",
        "starts_at",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
        "starts_at",
        "expires_at",
    )

    search_fields = (
        "teacher__email",
        "khalti_pidx",
        "khalti_transaction_id",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Teacher",
            {"fields": ("teacher",)},
        ),
        (
            "Subscription Details",
            {
                "fields": (
                    "amount",
                    "duration_days",
                    "status",
                )
            },
        ),
        (
            "Validity Period",
            {
                "fields": (
                    "starts_at",
                    "expires_at",
                )
            },
        ),
        (
            "Payment (Khalti)",
            {
                "fields": (
                    "khalti_pidx",
                    "khalti_transaction_id",
                )
            },
        ),
        (
            "System Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = [
        "activate_subscription",
        "expire_subscription",
        "cancel_subscription",
    ]

    # -------------------------
    # Display helpers
    # -------------------------

    def teacher_email(self, obj):
        return obj.teacher.email

    teacher_email.short_description = "Teacher"

    def status_badge(self, obj):
        colors = {
            "pending": "#ffc107",
            "active": "#28a745",
            "expired": "#6c757d",
            "cancelled": "#dc3545",
        }

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.status, "#6c757d"),
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    # -------------------------
    # Admin actions
    # -------------------------

    def activate_subscription(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated} subscription(s) activated successfully.")

    activate_subscription.short_description = "Activate selected subscriptions"

    def expire_subscription(self, request, queryset):
        updated = queryset.update(status="expired")
        self.message_user(request, f"{updated} subscription(s) marked as expired.")

    expire_subscription.short_description = "Expire selected subscriptions"

    def cancel_subscription(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} subscription(s) cancelled.")

    cancel_subscription.short_description = "Cancel selected subscriptions"


@admin.register(GigPayment)
class GigPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "gig",
        "parent",
        "teacher",
        "amount",
        "platform_fee",
        "status",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "status",
        "created_at",
        "paid_at",
    )

    search_fields = (
        "gig__title",
        "parent__email",
        "teacher__email",
        "khalti_pidx",
        "khalti_transaction_id",
    )

    readonly_fields = (
        "amount",
        "platform_fee",
        "khalti_pidx",
        "khalti_transaction_id",
        "created_at",
        "paid_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Gig & Users",
            {
                "fields": ("gig", "parent", "teacher"),
            },
        ),
        (
            "Payment Breakdown",
            {
                "fields": (
                    "amount",
                    "platform_fee",
                ),
            },
        ),
        (
            "Payment Status",
            {
                "fields": ("status",),
            },
        ),
        (
            "Khalti Details",
            {
                "fields": (
                    "khalti_pidx",
                    "khalti_transaction_id",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "paid_at",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        """
        Payments must be created programmatically
        """
        return False
