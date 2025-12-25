from django.db import models
from accounts.models import User


class Notification(models.Model):
    TYPE_CHOICES = [
        ("application_received", "Application Received"),
        ("teacher_selected", "Teacher Selected"),
        ("selection_accepted", "Selection Accepted"),
        ("selection_rejected", "Selection Rejected"),
        ("payment_initiated", "Payment Initiated"),
        ("escrow_funded", "Escrow Funded"),
        ("gig_started", "Gig Started"),
        ("completion_requested", "Completion Requested"),
        ("payment_released", "Payment Released"),
        ("gig_cancelled", "Gig Cancelled"),
        ("dispute_opened", "Dispute Opened"),
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
