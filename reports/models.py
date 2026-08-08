from django.db import models
from users.models import User

class Report(models.Model):
    TARGET_CHOICES = [('product', 'منتج'), ('entity', 'جهة')]
    STATUS_CHOICES = [('pending', 'قيد المراجعة'), ('resolved', 'تم الحل')]

    target_type = models.CharField(max_length=10, choices=TARGET_CHOICES)
    target_id = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(
    'users.User', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.target_type} - {self.status}"