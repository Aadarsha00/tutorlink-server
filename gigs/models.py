from django.db import models
from accounts.models import User


class Gig(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("selection_pending", "Selection Pending"),
        ("confirmation_pending", "Confirmation Pending"),
        ("payment_pending", "Payment Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("disputed", "Disputed"),
    ]

    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gigs")
    title = models.CharField(max_length=300)
    subject = models.CharField(max_length=100)
    grade = models.CharField(max_length=50)
    description = models.TextField()
    budget_min = models.DecimalField(max_digits=10, decimal_places=2)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2)
    schedule = models.JSONField()  # {day: time, frequency}
    location = models.CharField(max_length=200)
    duration_weeks = models.IntegerField()
    sessions_per_week = models.IntegerField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    selected_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_gigs",
    )
    hired_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hired_gigs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    boosted_until = models.DateTimeField(null=True, blank=True)
    boost_plan_id = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["subject", "grade"]),
            models.Index(fields=["boosted_until", "-created_at"]),
        ]
