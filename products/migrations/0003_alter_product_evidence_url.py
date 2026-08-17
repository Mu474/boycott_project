from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_alter_product_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='evidence_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
