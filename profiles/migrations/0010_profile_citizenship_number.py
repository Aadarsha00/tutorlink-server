from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0009_split_teacher_citizenship_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacherprofile",
            name="citizenship_number",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="parentprofile",
            name="citizenship_number",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
