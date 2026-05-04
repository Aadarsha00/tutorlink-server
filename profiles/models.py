# profiles/models.py
from django.db import models
from django.db.models import Avg
from accounts.models import User
from django.conf import settings
import uuid
import os

# ============================================
# LOOKUP/CHOICE MODELS
# ============================================


class Subject(models.Model):
    """Subject choices for teachers"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Grade(models.Model):
    """Grade/Class choices for teachers"""

    name = models.CharField(
        max_length=50, unique=True
    )  # "Grade 1", "Grade 10", "A-Level", etc.
    order = models.IntegerField(default=0)  # For sorting
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ============================================
# RATING MODEL
# ============================================


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
    score = models.PositiveSmallIntegerField()  # 1-5 enforced at serializer level
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("rater", "gig")
        indexes = [
            models.Index(fields=["ratee"]),
            models.Index(fields=["score"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.rater} → {self.ratee} ({self.score})"


# ============================================
# PROFILE MODELS
# ============================================


def get_kyc_photo_upload_path(instance, filename):
    """Generate dynamic upload path for KYC photos"""
    ext = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    from datetime import datetime

    now = datetime.now()
    return os.path.join(
        "kyc_photos",
        str(instance.user.id),
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        unique_filename,
    )


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

    # Many-to-many relationships
    subjects = models.ManyToManyField(Subject, related_name="teachers")
    grades = models.ManyToManyField(Grade, related_name="teachers")

    location = models.CharField(max_length=200)
    address = models.TextField()
    hourly_rate_min = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate_max = models.DecimalField(max_digits=10, decimal_places=2)
    bio = models.TextField()

    # KYC Photo
    kyc_photo = models.ImageField(
        upload_to=get_kyc_photo_upload_path,
        max_length=500,
        null=True,
        blank=True,
        help_text="Photo with clear visibility of face, eyes, and ears for KYC verification",
    )
    kyc_photo_verified = models.BooleanField(
        default=False,
        help_text="Whether the KYC photo has been verified by admin",
    )
    kyc_photo_rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for KYC photo rejection",
    )

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default="pending"
    )
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_premium", "verification_status"]),
            models.Index(fields=["location"]),
        ]

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


class TeacherAvailability(models.Model):
    """Teacher availability schedule"""

    DAYS_OF_WEEK = [
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        ("saturday", "Saturday"),
        ("sunday", "Sunday"),
    ]

    teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, related_name="availability_slots"
    )
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["teacher", "day_of_week"]),
        ]

    def __str__(self):
        return f"{self.teacher.full_name} - {self.get_day_of_week_display()}: {self.start_time}-{self.end_time}"


# ============================================
# TEACHER DOCUMENT MODEL
# ============================================


def get_teacher_document_upload_path(instance, filename):
    """
    Generate dynamic upload path for teacher documents
    Format: teacher_documents/user_id/YYYY/MM/DD/uuid_filename.ext
    """
    ext = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    from datetime import datetime

    now = datetime.now()

    return os.path.join(
        "teacher_documents",
        str(instance.teacher.user.id),
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        unique_filename,
    )


class VerificationDocument(models.Model):
    """Documents uploaded for teacher verification"""

    DOCUMENT_TYPE = [
        ("citizenship_front", "Citizenship Front"),
        ("citizenship_back", "Citizenship Back"),
        ("academic", "Academic Certificate"),
        ("experience", "Experience Letter"),
        ("other", "Other"),
    ]

    teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(
        upload_to=get_teacher_document_upload_path, max_length=500, null=True
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    verified = models.BooleanField(null=True, blank=True, default=None)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_teacher_documents",
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["teacher", "-uploaded_at"]),
            models.Index(fields=["verified"]),
        ]

    def __str__(self):
        return f"{self.teacher.full_name} - {self.get_document_type_display()}"

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    def delete(self, *args, **kwargs):
        """Delete file when model is deleted"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


# ============================================
# PARENT PROFILE AND DOCUMENT MODELS
# ============================================


def get_parent_kyc_photo_upload_path(instance, filename):
    """Generate dynamic upload path for parent KYC photos"""
    ext = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    from datetime import datetime

    now = datetime.now()
    return os.path.join(
        "kyc_photos",
        "parent",
        str(instance.user.id),
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        unique_filename,
    )


class ParentProfile(models.Model):
    VERIFICATION_STATUS = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="parent_profile"
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=200)
    address = models.TextField()

    # KYC Photo
    kyc_photo = models.ImageField(
        upload_to=get_parent_kyc_photo_upload_path,
        max_length=500,
        null=True,
        blank=True,
        help_text="Photo with clear visibility of face, eyes, and ears for KYC verification",
    )
    kyc_photo_verified = models.BooleanField(
        default=False,
        help_text="Whether the KYC photo has been verified by admin",
    )
    kyc_photo_rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for KYC photo rejection",
    )

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def average_rating(self):
        return (
            self.user.ratings_received.filter(rater_type="teacher").aggregate(
                avg=Avg("score")
            )["avg"]
            or 0
        )

    @property
    def total_reviews(self):
        return self.user.ratings_received.filter(rater_type="teacher").count()

    def __str__(self):
        return self.full_name


def get_parent_document_upload_path(instance, filename):
    """
    Generate dynamic upload path for parent documents
    Format: parent_documents/user_id/YYYY/MM/DD/uuid_filename.ext
    """
    ext = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    from datetime import datetime

    now = datetime.now()

    return os.path.join(
        "parent_documents",
        str(instance.parent.user.id),
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        unique_filename,
    )


class ParentVerificationDocument(models.Model):
    """Documents uploaded for parent verification"""

    DOCUMENT_TYPE = [
        ("citizenship_front", "Citizenship Front"),
        ("citizenship_back", "Citizenship Back"),
        ("id_card", "ID Card"),
        ("supporting_document", "Supporting Document"),
    ]

    parent = models.ForeignKey(
        ParentProfile, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(upload_to=get_parent_document_upload_path, max_length=500)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE)
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    verified = models.BooleanField(null=True, blank=True, default=None)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_parent_documents",
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["parent", "-uploaded_at"]),
            models.Index(fields=["verified"]),
        ]

    def __str__(self):
        return f"{self.parent.full_name} - {self.get_document_type_display()}"

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    def delete(self, *args, **kwargs):
        """Delete file when model is deleted"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
