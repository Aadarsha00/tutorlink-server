from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gigs", "0002_gig_boost_fields"),
        ("payments", "0003_remove_gigpayment_teacher_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="premiumsubscription",
            name="billing_cycle",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="premiumsubscription",
            name="plan_id",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.CreateModel(
            name="GigBoostPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("plan_id", models.CharField(max_length=50)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("duration_days", models.IntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("refunded", "Refunded"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "khalti_pidx",
                    models.CharField(
                        blank=True, max_length=100, null=True, unique=True
                    ),
                ),
                (
                    "khalti_transaction_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                (
                    "gig",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="boost_payments",
                        to="gigs.gig",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gig_boost_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="gigboostpayment",
            index=models.Index(
                fields=["gig", "status"], name="payments_gi_gig_id_fca5d7_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gigboostpayment",
            index=models.Index(
                fields=["parent", "status"], name="payments_gi_parent__8492c3_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="gigboostpayment",
            index=models.Index(
                fields=["khalti_pidx"], name="payments_gi_khalti__c28f37_idx"
            ),
        ),
    ]
