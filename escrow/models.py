from django.db import models
from accounts.models import User
from gigs.models import Gig


class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("pending_payment", "Pending Payment"),
        ("funded", "Funded"),
        ("held", "Held"),
        ("released", "Released"),
        ("refunded", "Refunded"),
        ("disputed", "Disputed"),
    ]

    gig = models.OneToOneField(Gig, on_delete=models.CASCADE, related_name="escrow")
    parent = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="escrow_payments"
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="escrow_earnings"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    teacher_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="initiated"
    )
    payment_method = models.CharField(max_length=50, default="khalti")
    khalti_token = models.CharField(max_length=200, null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=200, null=True, blank=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]


class EscrowAction(models.Model):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("payment_initiated", "Payment Initiated"),
        ("payment_verified", "Payment Verified"),
        ("held", "Held"),
        ("completion_requested", "Completion Requested"),
        ("released", "Released"),
        ("refunded", "Refunded"),
        ("disputed", "Disputed"),
    ]

    escrow = models.ForeignKey(
        EscrowTransaction, on_delete=models.CASCADE, related_name="actions"
    )
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
