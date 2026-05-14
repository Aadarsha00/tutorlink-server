from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gigs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="gig",
            name="boost_plan_id",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="gig",
            name="boosted_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="gig",
            index=models.Index(
                fields=["boosted_until", "-created_at"],
                name="gigs_gig_boosted_695d0e_idx",
            ),
        ),
    ]
