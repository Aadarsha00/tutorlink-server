from django.contrib import admin
from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "school_name",
        "subject",
        "location",
        "status",
        "deadline",
        "created_at",
    ]
    list_filter = ["status", "employment_type", "subject", "created_at"]
    search_fields = ["title", "school_name", "subject", "location"]
    readonly_fields = ["created_at", "updated_at", "published_at", "closed_at"]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["job", "teacher", "status", "cv_document", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["job__title", "job__school_name", "teacher__email"]
    readonly_fields = ["created_at", "updated_at"]
