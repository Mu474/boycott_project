from django.db import models
from categories.models import Category

class BusinessEntity(models.Model):
    STATUS_CHOICES = [
    ('boycott', 'مقاطعة'),
    ('caution', 'حذر'),
    ('alternative', 'بديل'),
    ]

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='entities/', blank=True, null=True)
    status = models.CharField(max_length=11, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True, null=True)
    # كان 200 حرف افتراضيًا (حد Django القياسي)، ووجدنا فعليًا روابط
    # مصادر حقيقية أطول من هذا (مثلاً روابط فيها معرّفات تتبّع طويلة).
    # وسّعناه بدل ما نقطع أي رابط حقيقي.
    evidence_url = models.URLField(max_length=500, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    parent_entity = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidiaries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
