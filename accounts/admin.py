# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model"""

    list_display = (
        "email",
        "role_badge",
        "full_name",
        "is_active_badge",
        "is_email_verified_badge",
        "is_staff",
        "created_at",
    )
    list_filter = (
        "role",
        "is_active",
        "is_email_verified",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "first_name",
                    "last_name",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")

    def get_readonly_fields(self, request, obj=None):
        """Make email readonly when editing existing user"""
        if obj:  # Editing an existing object
            return self.readonly_fields + ("email",)
        return self.readonly_fields

    def full_name(self, obj):
        """Display full name in list"""
        return obj.get_full_name()

    full_name.short_description = "Full Name"

    def role_badge(self, obj):
        """Display role as colored badge"""
        colors = {
            "teacher": "#28a745",  # Green
            "parent": "#007bff",  # Blue
            "admin": "#dc3545",  # Red
        }
        color = colors.get(obj.role, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_role_display(),
        )

    role_badge.short_description = "Role"

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-size: 18px;">{}</span>',
                "✓",
            )
        return format_html(
            '<span style="color: red; font-size: 18px;">{}</span>',
            "✗",
        )

    is_active_badge.short_description = "Active"

    def is_email_verified_badge(self, obj):
        if obj.is_email_verified:
            return format_html(
                '<span style="color: green; font-size: 18px;">{}</span>',
                "✓",
            )
        return format_html(
            '<span style="color: orange; font-size: 18px;">{}</span>',
            "✗",
        )

    is_email_verified_badge.short_description = "Verified"

    actions = ["activate_users", "deactivate_users", "verify_emails"]

    def activate_users(self, request, queryset):
        """Bulk activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) successfully activated.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) successfully deactivated.")

    deactivate_users.short_description = "Deactivate selected users"

    def verify_emails(self, request, queryset):
        """Bulk verify user emails"""
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f"{updated} user email(s) successfully verified.")

    verify_emails.short_description = "Verify selected user emails"
