from django.conf import settings
from django.db import models


class UserReport(models.Model):
    CATEGORY_CHOICES = [
        ("bug", "Bug"),
        ("content", "Content"),
        ("user", "User"),
        ("message", "Message"),
        ("payment", "Payment"),
        ("dispute", "Dispute"),
        ("safety", "Safety"),
        ("other", "Other"),
    ]
    TARGET_CHOICES = [
        ("bug", "Bug"),
        ("user", "User"),
        ("profile", "Profile"),
        ("gig", "Gig"),
        ("job", "Job"),
        ("application", "Application"),
        ("message", "Message"),
        ("document", "Document"),
        ("payment", "Payment"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_review", "In Review"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submitted_reports",
    )
    reporter_email = models.EmailField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target_label = models.CharField(max_length=250, blank=True)
    page_url = models.CharField(max_length=700, blank=True)
    title = models.CharField(max_length=180)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_reports",
    )
    resolution_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "target_type"]),
            models.Index(fields=["reporter", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()} report #{self.id}: {self.title}"
