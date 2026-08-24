from django.db import models
from users.models import User

class Suggestion(models.Model):
    TYPE_CHOICES = [('add', 'إضافة'), ('edit', 'تعديل')]
    TARGET_CHOICES = [('product', 'منتج'), ('entity', 'جهة')]
    STATUS_CHOICES = [('pending', 'قيد المراجعة'), ('approved', 'مقبول'), ('rejected', 'مرفوض')]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    target_type = models.CharField(max_length=10, choices=TARGET_CHOICES)
    target_id = models.IntegerField(null=True, blank=True)
    data_json = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    # سبب الرفض — يظهر للمستخدم بإشعاره لو رُفض اقتراحه (راجع
    # notifications/services.py). اختياري لأن بعض الرفض واضح بدون شرح
    rejection_reason = models.TextField(blank=True, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(
    'users.User', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.target_type}"
