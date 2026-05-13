from django.db import migrations


def create_existing_conversations(apps, schema_editor):
    Gig = apps.get_model("gigs", "Gig")
    Conversation = apps.get_model("messaging", "Conversation")

    eligible_gigs = Gig.objects.filter(
        status__in=["payment_pending", "active", "completed"],
        hired_teacher__isnull=False,
    )

    for gig in eligible_gigs:
        Conversation.objects.get_or_create(
            gig_id=gig.id,
            defaults={
                "parent_id": gig.parent_id,
                "teacher_id": gig.hired_teacher_id,
                "is_active": True,
            },
        )


def delete_backfilled_conversations(apps, schema_editor):
    Conversation = apps.get_model("messaging", "Conversation")
    Conversation.objects.filter(messages__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0001_initial"),
        ("gigs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_existing_conversations,
            reverse_code=delete_backfilled_conversations,
        ),
    ]
