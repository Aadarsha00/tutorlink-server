from django.db import models
from accounts.models import User
from gigs.models import Gig


class Application(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("selected", "Selected"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name="applications")
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="applications"
    )
    cover_letter = models.TextField()
    proposed_rate = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    selected_at = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    match_cancelled_at = models.DateTimeField(null=True, blank=True)
    match_cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_matches",
    )
    match_cancel_reason = models.CharField(max_length=300, blank=True)
    rate_change_proposed_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    rate_change_proposed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rate_change_proposals",
    )
    rate_change_proposed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["gig", "teacher"]
        indexes = [
            models.Index(fields=["teacher", "status"]),
            models.Index(fields=["gig", "status"]),
        ]
