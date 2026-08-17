from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_alter_product_evidence_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='reason_en',
            field=models.TextField(blank=True, null=True),
        ),
    ]
