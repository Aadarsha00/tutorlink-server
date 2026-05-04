from django.db import models
from accounts.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        # Application notifications
        ("application_received", "Application Received"),
        ("teacher_selected", "Teacher Selected"),
        ("selection_accepted", "Selection Accepted"),
        ("selection_rejected", "Selection Rejected"),
        # Gig notifications
        ("gig_started", "Gig Started"),
        ("gig_completed", "Gig Completed"),
        ("gig_cancelled", "Gig Cancelled"),
        # Admin notifications
        ("completion_requested", "Completion Requested"),
        ("dispute_opened", "Dispute Opened"),
        ("dispute_resolved", "Dispute Resolved"),
        # Premium notifications (for teachers)
        ("premium_activated", "Premium Activated"),
        ("premium_expiring", "Premium Expiring Soon"),
        ("premium_expired", "Premium Expired"),
        # Document notifications
        ("document_verified", "Document Verified"),
        ("document_rejected", "Document Rejected"),
        ("document_uploaded", "Document Uploaded"),
        # System notifications (for all)
        ("system_announcement", "System Announcement"),
        ("test", "Test Notification"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]
