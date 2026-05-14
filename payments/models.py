from django.db import models
from accounts.models import User
from gigs.models import Gig
from decimal import Decimal


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

    plan_id = models.CharField(max_length=50, blank=True, default="")
    billing_cycle = models.CharField(max_length=20, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField()

    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    khalti_pidx = models.CharField(max_length=200, null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GigPayment(models.Model):
    """Payment for unlocking teacher contact details"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    gig = models.OneToOneField(Gig, on_delete=models.CASCADE, related_name="payment")
    parent = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="gig_payments"
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Khalti payment fields
    khalti_pidx = models.CharField(max_length=100, unique=True, null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=100, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["parent", "status"]),
            models.Index(fields=["teacher", "status"]),
            models.Index(fields=["khalti_pidx"]),
        ]

    def __str__(self):
        return f"Payment for {self.gig.title} - {self.status}"

    @classmethod
    def calculate_amounts(cls, gig_amount):
        """Calculate platform fee (10%)"""
        platform_fee = gig_amount * Decimal("0.10")
        return {
            "amount": gig_amount,
            "platform_fee": platform_fee,
        }


class GigBoostPayment(models.Model):
    """Payment for promoting a parent's open gig in teacher listings."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name="boost_payments")
    parent = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="gig_boost_payments"
    )
    plan_id = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    khalti_pidx = models.CharField(max_length=100, unique=True, null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["gig", "status"]),
            models.Index(fields=["parent", "status"]),
            models.Index(fields=["khalti_pidx"]),
        ]

    def __str__(self):
        return f"Boost for {self.gig.title} - {self.status}"
