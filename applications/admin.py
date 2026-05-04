from django.contrib import admin
from django.utils.html import format_html
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "gig",
        "teacher_email",
        "status_badge",
        "proposed_rate",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "teacher__email",
        "gig__title",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "selected_at",
        "responded_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "gig",
                    "teacher",
                    "cover_letter",
                    "proposed_rate",
                    "status",
                )
            },
        ),
        (
            "Timeline",
            {
                "fields": (
                    "selected_at",
                    "response_deadline",
                    "responded_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = [
        "mark_selected",
        "mark_accepted",
        "mark_rejected",
        "mark_withdrawn",
        "mark_expired",
    ]

    # -------------------------
    # Display helpers
    # -------------------------

    def teacher_email(self, obj):
        return obj.teacher.email

    teacher_email.short_description = "Teacher"

    def status_badge(self, obj):
        colors = {
            "pending": "#6c757d",
            "selected": "#17a2b8",
            "accepted": "#28a745",
            "rejected": "#dc3545",
            "withdrawn": "#fd7e14",
            "expired": "#343a40",
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

    def mark_selected(self, request, queryset):
        updated = queryset.update(status="selected")
        self.message_user(request, f"{updated} application(s) marked as selected.")

    mark_selected.short_description = "Mark selected applications"

    def mark_accepted(self, request, queryset):
        updated = queryset.update(status="accepted")
        self.message_user(request, f"{updated} application(s) accepted.")

    mark_accepted.short_description = "Mark accepted applications"

    def mark_rejected(self, request, queryset):
        updated = queryset.update(status="rejected")
        self.message_user(request, f"{updated} application(s) rejected.")

    mark_rejected.short_description = "Mark rejected applications"

    def mark_withdrawn(self, request, queryset):
        updated = queryset.update(status="withdrawn")
        self.message_user(request, f"{updated} application(s) withdrawn.")

    mark_withdrawn.short_description = "Mark withdrawn applications"

    def mark_expired(self, request, queryset):
        updated = queryset.update(status="expired")
        self.message_user(request, f"{updated} application(s) expired.")

    mark_expired.short_description = "Mark expired applications"
