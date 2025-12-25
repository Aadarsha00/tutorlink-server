from django.db import models
from django.db.models import Avg
from accounts.models import User


class Rating(models.Model):
    RATER_TYPE = (
        ("parent", "Parent"),
        ("teacher", "Teacher"),
    )

    rater = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings_given"
    )

    ratee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings_received"
    )

    gig = models.ForeignKey(
        "gigs.Gig", on_delete=models.CASCADE, related_name="ratings"
    )

    rater_type = models.CharField(max_length=10, choices=RATER_TYPE)

    score = models.PositiveSmallIntegerField()  # 1–5 enforced at serializer level
    review = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("rater", "gig")
        indexes = [
            models.Index(fields=["ratee"]),
            models.Index(fields=["score"]),
        ]

    def __str__(self):
        return f"{self.rater} → {self.ratee} ({self.score})"


class TeacherProfile(models.Model):
    VERIFICATION_STATUS = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile"
    )

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    education = models.TextField()
    experience_years = models.IntegerField()

    subjects = models.JSONField()  # ["Math", "Physics"]
    grades = models.JSONField()  # ["10", "11", "12"]

    location = models.CharField(max_length=200)
    address = models.TextField()

    hourly_rate_min = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate_max = models.DecimalField(max_digits=10, decimal_places=2)

    availability = models.JSONField()  # {"Mon": ["7-9"], "Tue": ["5-7"]}

    bio = models.TextField()

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default="pending"
    )

    verification_documents = models.JSONField(null=True, blank=True)

    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_premium", "verification_status"]),
            models.Index(fields=["location"]),
        ]

    # -------------------------
    # Rating Aggregates
    # -------------------------

    @property
    def average_rating(self):
        return (
            self.user.ratings_received.filter(rater_type="parent").aggregate(
                avg=Avg("score")
            )["avg"]
            or 0
        )

    @property
    def total_reviews(self):
        return self.user.ratings_received.filter(rater_type="parent").count()

    def __str__(self):
        return self.full_name


class ParentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="parent_profile"
    )

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=200)
    address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional: teacher → parent ratings
    @property
    def average_rating(self):
        return (
            self.user.ratings_received.filter(rater_type="teacher").aggregate(
                avg=Avg("score")
            )["avg"]
            or 0
        )

    def __str__(self):
        return self.full_name
