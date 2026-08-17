from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entities', '0003_alter_businessentity_evidence_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessentity',
            name='countries',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='businessentity',
            name='reason_en',
            field=models.TextField(blank=True, null=True),
        ),
    ]
