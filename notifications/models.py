from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    إشعارات داخل التطبيق (in-app) — تظهر لما يفتح المستخدم التطبيق أو
    شاشة الإشعارات، مو push حقيقي يوصل والتطبيق مقفول. الـ push
    الحقيقي (عبر Firebase Cloud Messaging) يحتاج مشروع Firebase منفصل
    (حساب المستخدم لازم يعدّه بنفسه بلوحة تحكم Firebase، ما أقدر أسويه
    كاملًا من مكاني)، فهذا أساس نقدر نبنيه ونختبره بالكامل الآن، وبعدين
    يُضاف push فوقه كطبقة اختيارية لاحقًا بدون ما يغيّر شيء بهذا الموديل.
    """
    TYPE_CHOICES = [
        ('suggestion_approved', 'اقتراح مقبول'),
        ('suggestion_rejected', 'اقتراح مرفوض'),
        ('report_resolved', 'بلاغ محلول'),
        ('post_published', 'منشور مجتمعي مقبول'),
        ('post_rejected', 'منشور مجتمعي مرفوض'),
        ('general', 'عام'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    # مرجع اختياري (id الاقتراح/البلاغ) — يسمح للواجهة تتنقل مباشرة
    # لمكان ذي علاقة مستقبلًا (لما تُبنى شاشة "اقتراحاتي")، بدون ما
    # يكون إلزاميًا الآن
    related_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read'])]
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'

    def __str__(self):
        return f'{self.user} - {self.title}'
