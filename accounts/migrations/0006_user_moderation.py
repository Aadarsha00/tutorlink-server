from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_user_profile_picture_verification"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="moderated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="moderation_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="suspended_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="moderated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="moderated_users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
