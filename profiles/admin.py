# profiles/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Subject,
    Grade,
    Rating,
    TeacherProfile,
    TeacherAvailability,
    VerificationDocument,
    ParentProfile,
)


# ============================================
# LOOKUP/CHOICE MODEL ADMINS
# ============================================


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "teacher_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    def teacher_count(self, obj):
        return obj.teachers.count()

    teacher_count.short_description = "Number of Teachers"


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_active", "teacher_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name"]
    ordering = ["order", "name"]

    def teacher_count(self, obj):
        return obj.teachers.count()

    teacher_count.short_description = "Number of Teachers"


# ============================================
# INLINE ADMINS
# ============================================


class TeacherAvailabilityInline(admin.TabularInline):
    model = TeacherAvailability
    extra = 1
    fields = ["day_of_week", "start_time", "end_time", "is_available"]


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    fields = [
        "document_type",
        "file_name",
        "file_url",
        "file_size",
        "verified",
        "verified_at",
    ]
    readonly_fields = ["uploaded_at"]

    def has_add_permission(self, request, obj=None):
        # Disable adding documents directly from the inline
        # Documents should be uploaded through the API
        return False


# ============================================
# TEACHER PROFILE ADMIN
# ============================================


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "user_email",
        "phone",
        "location",
        "verification_status",
        "is_premium",
        "average_rating",
        "total_reviews",
        "created_at",
    ]
    list_filter = [
        "verification_status",
        "is_premium",
        "created_at",
        "subjects",
        "grades",
    ]
    search_fields = ["full_name", "user__email", "phone", "location"]
    readonly_fields = [
        "average_rating",
        "total_reviews",
        "created_at",
        "updated_at",
    ]
    filter_horizontal = ["subjects", "grades"]
    inlines = [TeacherAvailabilityInline, VerificationDocumentInline]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "user",
                    "full_name",
                    "phone",
                    "location",
                    "address",
                )
            },
        ),
        (
            "Professional Details",
            {
                "fields": (
                    "education",
                    "experience_years",
                    "subjects",
                    "grades",
                    "hourly_rate_min",
                    "hourly_rate_max",
                    "bio",
                )
            },
        ),
        (
            "Verification & Premium",
            {
                "fields": (
                    "verification_status",
                    "is_premium",
                    "premium_expires_at",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "average_rating",
                    "total_reviews",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    def average_rating(self, obj):
        rating = obj.average_rating
        if rating > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} ⭐</span>',
                f'{rating:.2f}',
            )
        return "No ratings"

    average_rating.short_description = "Avg Rating"

    def total_reviews(self, obj):
        return obj.total_reviews

    total_reviews.short_description = "Reviews"

    actions = ["verify_profiles", "reject_profiles", "make_premium"]

    def verify_profiles(self, request, queryset):
        updated = queryset.update(verification_status="verified")
        self.message_user(request, f"{updated} teacher(s) verified successfully.")

    verify_profiles.short_description = "Verify selected teachers"

    def reject_profiles(self, request, queryset):
        updated = queryset.update(verification_status="rejected")
        self.message_user(request, f"{updated} teacher(s) rejected.")

    reject_profiles.short_description = "Reject selected teachers"

    def make_premium(self, request, queryset):
        from datetime import timedelta

        for teacher in queryset:
            if not teacher.is_premium:
                teacher.is_premium = True
                teacher.premium_expires_at = timezone.now() + timedelta(days=30)
                teacher.save()
        self.message_user(
            request, f"{queryset.count()} teacher(s) upgraded to premium (30 days)."
        )

    make_premium.short_description = "Make premium (30 days)"


# ============================================
# PARENT PROFILE ADMIN
# ============================================


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "user_email",
        "phone",
        "location",
        "average_rating",
        "total_reviews",
        "created_at",
    ]
    list_filter = ["created_at", "location"]
    search_fields = ["full_name", "user__email", "phone", "location"]
    readonly_fields = ["average_rating", "total_reviews", "created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "user",
                    "full_name",
                    "phone",
                    "location",
                    "address",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "average_rating",
                    "total_reviews",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    def average_rating(self, obj):
        rating = obj.average_rating
        if rating > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} ⭐</span>',
                f'{rating:.2f}',
            )
        return "No ratings"

    average_rating.short_description = "Avg Rating"

    def total_reviews(self, obj):
        return obj.total_reviews

    total_reviews.short_description = "Reviews"


# ============================================
# RATING ADMIN
# ============================================


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "rater_name",
        "ratee_name",
        "rater_type",
        "score_display",
        "gig_link",
        "created_at",
    ]
    list_filter = ["rater_type", "score", "created_at"]
    search_fields = [
        "rater__email",
        "rater__first_name",
        "rater__last_name",
        "ratee__email",
        "ratee__first_name",
        "ratee__last_name",
    ]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Rating Information",
            {
                "fields": (
                    "rater",
                    "ratee",
                    "gig",
                    "rater_type",
                    "score",
                    "review",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at",)}),
    )

    def rater_name(self, obj):
        return (
            f"{obj.rater.first_name} {obj.rater.last_name}".strip() or obj.rater.email
        )

    rater_name.short_description = "Rater"

    def ratee_name(self, obj):
        return (
            f"{obj.ratee.first_name} {obj.ratee.last_name}".strip() or obj.ratee.email
        )

    ratee_name.short_description = "Ratee"

    def score_display(self, obj):
        stars = "⭐" * obj.score
        color = (
            "#28a745" if obj.score >= 4 else "#ffc107" if obj.score >= 3 else "#dc3545"
        )
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ({})</span>',
            color,
            stars,
            obj.score,
        )

    score_display.short_description = "Score"

    def gig_link(self, obj):
        if obj.gig:
            url = reverse("admin:gigs_gig_change", args=[obj.gig.id])
            return format_html('<a href="{}">{}</a>', url, obj.gig.title)
        return "-"

    gig_link.short_description = "Gig"


# ============================================
# TEACHER AVAILABILITY ADMIN
# ============================================


@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        "teacher_name",
        "day_of_week",
        "start_time",
        "end_time",
        "is_available",
        "created_at",
    ]
    list_filter = ["day_of_week", "is_available", "created_at"]
    search_fields = ["teacher__full_name", "teacher__user__email"]
    ordering = ["teacher", "day_of_week", "start_time"]

    def teacher_name(self, obj):
        return obj.teacher.full_name

    teacher_name.short_description = "Teacher"


# ============================================
# VERIFICATION DOCUMENT ADMIN
# ============================================


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "teacher_name",
        "document_type",
        "file_name",
        "file_size_display",
        "verified",
        "uploaded_at",
    ]
    list_filter = ["document_type", "verified", "uploaded_at"]
    search_fields = ["teacher__full_name", "teacher__user__email", "file_name"]
    readonly_fields = ["uploaded_at"]
    ordering = ["-uploaded_at"]

    fieldsets = (
        (
            "Document Information",
            {
                "fields": (
                    "teacher",
                    "document_type",
                    "file_name",
                    "file_url",
                    "file_size",
                )
            },
        ),
        (
            "Verification",
            {"fields": ("verified", "verified_at", "notes")},
        ),
        ("Metadata", {"fields": ("uploaded_at",)}),
    )

    def teacher_name(self, obj):
        return obj.teacher.full_name

    teacher_name.short_description = "Teacher"

    def file_size_display(self, obj):
        size_kb = obj.file_size / 1024
        if size_kb < 1024:
            return f"{size_kb:.2f} KB"
        return f"{size_kb / 1024:.2f} MB"

    file_size_display.short_description = "File Size"

    actions = ["verify_documents", "unverify_documents"]

    def verify_documents(self, request, queryset):
        updated = queryset.update(verified=True, verified_at=timezone.now())
        self.message_user(request, f"{updated} document(s) verified successfully.")

    verify_documents.short_description = "Verify selected documents"

    def unverify_documents(self, request, queryset):
        updated = queryset.update(verified=False, verified_at=None)
        self.message_user(request, f"{updated} document(s) unverified.")

    unverify_documents.short_description = "Unverify selected documents"
