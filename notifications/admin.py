from django.contrib import admin
from django.utils.html import format_html
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_email",
        "type_badge",
        "title",
        "read_badge",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__email",
        "title",
        "message",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "read_at",
    )

    fieldsets = (
        (
            "Recipient",
            {"fields": ("user",)},
        ),
        (
            "Notification Content",
            {
                "fields": (
                    "notification_type",
                    "title",
                    "message",
                    "link",
                    "metadata",
                )
            },
        ),
        (
            "Read Status",
            {
                "fields": (
                    "is_read",
                    "read_at",
                    "created_at",
                )
            },
        ),
    )

    actions = [
        "mark_as_read",
        "mark_as_unread",
    ]

    # -------------------------
    # Display helpers
    # -------------------------

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def type_badge(self, obj):
        colors = {
            "application_received": "#007bff",
            "teacher_selected": "#17a2b8",
            "selection_accepted": "#28a745",
            "selection_rejected": "#dc3545",
            "gig_started": "#6610f2",
            "completion_requested": "#fd7e14",
            "payment_released": "#28a745",
            "gig_cancelled": "#6c757d",
            "dispute_opened": "#343a40",
        }

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.notification_type, "#6c757d"),
            obj.get_notification_type_display(),
        )

    type_badge.short_description = "Type"
    type_badge.admin_order_field = "notification_type"

    def read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                "Read",
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">{}</span>',
            "Unread",
        )

    read_badge.short_description = "Status"
    read_badge.admin_order_field = "is_read"

    # -------------------------
    # Admin actions
    # -------------------------

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")

    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")

    mark_as_unread.short_description = "Mark selected notifications as unread"
