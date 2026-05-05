from django.conf import settings
from django.db import models
from profiles.models import VerificationDocument


class Job(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full Time"),
        ("part_time", "Part Time"),
        ("contract", "Contract"),
        ("temporary", "Temporary"),
        ("internship", "Internship"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_jobs"
    )
    title = models.CharField(max_length=300)
    school_name = models.CharField(max_length=200)
    school_address = models.TextField()
    school_contact_email = models.EmailField(blank=True)
    school_contact_phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=100)
    grade = models.CharField(max_length=100, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default="full_time"
    )
    description = models.TextField()
    requirements = models.TextField()
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=200)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["subject", "location"]),
        ]

    def __str__(self):
        return f"{self.title} at {self.school_name}"


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("shortlisted", "Shortlisted"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_applications"
    )
    cv_document = models.ForeignKey(
        VerificationDocument,
        on_delete=models.PROTECT,
        related_name="job_applications",
        help_text="CV document copied from the teacher profile at apply time",
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["job", "teacher"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["teacher", "status"]),
            models.Index(fields=["job", "status"]),
        ]

    def __str__(self):
        return f"{self.teacher.email} -> {self.job.title}"
