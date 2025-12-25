from django.db import models
from accounts.models import User


class PremiumSubscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="premium_subscriptions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField()
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    khalti_token = models.CharField(max_length=200, null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "status"]),
        ]
