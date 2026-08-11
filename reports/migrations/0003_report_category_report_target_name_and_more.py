from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_alter_report_reviewed_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='category',
            field=models.CharField(
                choices=[
                    ('data_error', 'خطأ في بيانات منتج/جهة'),
                    ('app_bug', 'مشكلة تقنية بالتطبيق'),
                    ('other', 'أخرى'),
                ],
                default='data_error',
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name='report',
            name='target_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='report',
            name='target_type',
            field=models.CharField(
                blank=True,
                choices=[('product', 'منتج'), ('entity', 'جهة')],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='report',
            name='target_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
