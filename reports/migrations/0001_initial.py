from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reporter_email", models.EmailField(blank=True, max_length=254)),
                ("category", models.CharField(choices=[("bug", "Bug"), ("content", "Content"), ("user", "User"), ("message", "Message"), ("payment", "Payment"), ("dispute", "Dispute"), ("safety", "Safety"), ("other", "Other")], max_length=20)),
                ("target_type", models.CharField(choices=[("bug", "Bug"), ("user", "User"), ("profile", "Profile"), ("gig", "Gig"), ("job", "Job"), ("application", "Application"), ("message", "Message"), ("document", "Document"), ("payment", "Payment"), ("other", "Other")], max_length=20)),
                ("target_id", models.PositiveIntegerField(blank=True, null=True)),
                ("target_label", models.CharField(blank=True, max_length=250)),
                ("page_url", models.CharField(blank=True, max_length=700)),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField()),
                ("status", models.CharField(choices=[("open", "Open"), ("in_review", "In Review"), ("resolved", "Resolved"), ("dismissed", "Dismissed")], default="open", max_length=20)),
                ("priority", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")], default="medium", max_length=20)),
                ("resolution_note", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_reports", to=settings.AUTH_USER_MODEL)),
                ("reporter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["status", "-created_at"], name="reports_use_status_371ac9_idx"),
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["category", "target_type"], name="reports_use_categor_126e50_idx"),
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["reporter", "-created_at"], name="reports_use_reporte_320957_idx"),
        ),
    ]
