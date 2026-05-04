from django.contrib import admin
from django.utils.html import format_html
from .models import Gig


@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "parent_email",
        "subject",
        "grade",
        "budget_range",
        "status_badge",
        "created_at",
    )

    list_filter = (
        "status",
        "subject",
        "grade",
        "location",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "parent__email",
        "subject",
        "grade",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "published_at",
        "closed_at",
    )

    fieldsets = (
        (
            "Gig Details",
            {
                "fields": (
                    "parent",
                    "title",
                    "description",
                    "subject",
                    "grade",
                    "location",
                )
            },
        ),
        (
            "Budget & Schedule",
            {
                "fields": (
                    "budget_min",
                    "budget_max",
                    "schedule",
                    "duration_weeks",
                    "sessions_per_week",
                )
            },
        ),
        (
            "Teachers",
            {
                "fields": (
                    "selected_teacher",
                    "hired_teacher",
                )
            },
        ),
        (
            "Status & Lifecycle",
            {
                "fields": (
                    "status",
                    "published_at",
                    "closed_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = [
        "mark_open",
        "mark_active",
        "mark_completed",
        "mark_cancelled",
        "mark_disputed",
    ]

    # -------------------------
    # Display helpers
    # -------------------------

    def parent_email(self, obj):
        return obj.parent.email

    parent_email.short_description = "Parent"

    def budget_range(self, obj):
        return f"{obj.budget_min} – {obj.budget_max}"

    budget_range.short_description = "Budget"

    def status_badge(self, obj):
        colors = {
            "draft": "#6c757d",
            "open": "#007bff",
            "selection_pending": "#17a2b8",
            "confirmation_pending": "#ffc107",
            "payment_pending": "#fd7e14",
            "active": "#28a745",
            "completed": "#20c997",
            "cancelled": "#dc3545",
            "disputed": "#343a40",
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

    def mark_open(self, request, queryset):
        updated = queryset.update(status="open")
        self.message_user(request, f"{updated} gig(s) marked as open.")

    mark_open.short_description = "Mark gigs as open"

    def mark_active(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated} gig(s) marked as active.")

    mark_active.short_description = "Mark gigs as active"

    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} gig(s) marked as completed.")

    mark_completed.short_description = "Mark gigs as completed"

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} gig(s) cancelled.")

    mark_cancelled.short_description = "Cancel gigs"

    def mark_disputed(self, request, queryset):
        updated = queryset.update(status="disputed")
        self.message_user(request, f"{updated} gig(s) marked as disputed.")

    mark_disputed.short_description = "Mark gigs as disputed"
