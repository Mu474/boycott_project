from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entities', '0002_alter_businessentity_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businessentity',
            name='evidence_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
