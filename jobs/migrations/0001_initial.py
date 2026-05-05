# Generated manually for the TutorSpot jobs app.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profiles", "0009_split_teacher_citizenship_documents"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("school_name", models.CharField(max_length=200)),
                ("school_address", models.TextField()),
                ("school_contact_email", models.EmailField(blank=True, max_length=254)),
                ("school_contact_phone", models.CharField(blank=True, max_length=30)),
                ("subject", models.CharField(max_length=100)),
                ("grade", models.CharField(blank=True, max_length=100)),
                (
                    "employment_type",
                    models.CharField(
                        choices=[
                            ("full_time", "Full Time"),
                            ("part_time", "Part Time"),
                            ("contract", "Contract"),
                            ("temporary", "Temporary"),
                            ("internship", "Internship"),
                        ],
                        default="full_time",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField()),
                ("requirements", models.TextField()),
                ("salary_min", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("salary_max", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("location", models.CharField(max_length=200)),
                ("deadline", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("open", "Open"),
                            ("closed", "Closed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_jobs", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="JobApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cover_letter", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("reviewed", "Reviewed"),
                            ("shortlisted", "Shortlisted"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("withdrawn", "Withdrawn"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("admin_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cv_document",
                    models.ForeignKey(
                        help_text="CV document copied from the teacher profile at apply time",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="job_applications",
                        to="profiles.verificationdocument",
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="jobs.job"),
                ),
                (
                    "teacher",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_applications", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("job", "teacher")},
            },
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["status", "-created_at"], name="jobs_job_status_57b86b_idx"),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["subject", "location"], name="jobs_job_subject_3b2dc6_idx"),
        ),
        migrations.AddIndex(
            model_name="jobapplication",
            index=models.Index(fields=["teacher", "status"], name="jobs_jobapp_teacher_1929aa_idx"),
        ),
        migrations.AddIndex(
            model_name="jobapplication",
            index=models.Index(fields=["job", "status"], name="jobs_jobapp_job_id_08192b_idx"),
        ),
    ]
