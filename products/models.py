from django.db import models
from categories.models import Category
from entities.models import BusinessEntity

class Product(models.Model):
    STATUS_CHOICES = [
        ('boycott', 'مقاطعة'),
        ('caution', 'حذر'),
        ('alternative', 'بديل'),
    ]

    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    barcode = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=11, choices=STATUS_CHOICES)

    # نفس منطق موديل الجهات — reason عربي (يُعرض بالتطبيق كما هو)،
    # reason_en يحتفظ بالنص الإنجليزي الأصلي لأي استيراد مستقبلي
    reason = models.TextField(blank=True, null=True)
    reason_en = models.TextField(blank=True, null=True)

    # نفس تعديل موديل الجهات — وسّعناه لنفس السبب (روابط مصادر طويلة)
    evidence_url = models.URLField(max_length=500, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    entity = models.ForeignKey(BusinessEntity, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
