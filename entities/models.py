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

    # reason صار الحقل العربي (يُعرض بالتطبيق كما هو، بدون أي تعديل
    # بجهة Flutter). reason_en يحتفظ بالنص الإنجليزي الأصلي المصدري —
    # لأهداف التوثيق العلمي، ولاستخدامه لاحقًا لما يُبنى دعم إنجليزي
    # فعلي بالتطبيق.
    reason = models.TextField(blank=True, null=True)
    reason_en = models.TextField(blank=True, null=True)

    # كان 200 حرف افتراضيًا (حد Django القياسي)، ووجدنا فعليًا روابط
    # مصادر حقيقية أطول من هذا (مثلاً روابط فيها معرّفات تتبّع طويلة).
    # وسّعناه بدل ما نقطع أي رابط حقيقي.
    evidence_url = models.URLField(max_length=500, blank=True, null=True)

    # تخزين خام لقائمة الدول المرتبطة (من مصادر الاستيراد) — غير
    # مُستخدم بواجهة التطبيق حاليًا، محفوظ للاستفادة منه مستقبلًا
    # (مثلاً فلترة حسب الدولة). صيغة نص مفصول بفواصل، بسيطة عمدًا.
    countries = models.CharField(max_length=300, blank=True, default='')

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
