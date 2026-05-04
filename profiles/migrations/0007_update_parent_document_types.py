from django.db import migrations, models


def split_existing_citizenship_documents(apps, schema_editor):
    ParentVerificationDocument = apps.get_model(
        "profiles", "ParentVerificationDocument"
    )
    ParentVerificationDocument.objects.filter(document_type="citizenship").update(
        document_type="citizenship_front"
    )
    ParentVerificationDocument.objects.filter(document_type="other").update(
        document_type="supporting_document"
    )


def restore_old_parent_document_types(apps, schema_editor):
    ParentVerificationDocument = apps.get_model(
        "profiles", "ParentVerificationDocument"
    )
    ParentVerificationDocument.objects.filter(document_type="citizenship_front").update(
        document_type="citizenship"
    )
    ParentVerificationDocument.objects.filter(document_type="citizenship_back").update(
        document_type="citizenship"
    )
    ParentVerificationDocument.objects.filter(
        document_type="supporting_document"
    ).update(document_type="other")


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0006_parentverificationdocument_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parentverificationdocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("citizenship_front", "Citizenship Front"),
                    ("citizenship_back", "Citizenship Back"),
                    ("id_card", "ID Card"),
                    ("supporting_document", "Supporting Document"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(
            split_existing_citizenship_documents,
            restore_old_parent_document_types,
        ),
    ]
