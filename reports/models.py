from django.db import models
from users.models import User

class Report(models.Model):
    # 'community_post' و'comment' — تعميم سليم مو حشر قسري: target_type/
    # target_id أصلًا مصمّمان بشكل عام (مرجع بولي-مورفيك بسيط)، عكس
    # Suggestion اللي له سلوك اعتماد محدّد (إنشاء سجل). 'comment' أُضيف
    # مع نظام التعليقات الجديد — نفس مبدأ الإبلاغ عن منشور بالضبط
    TARGET_CHOICES = [
        ('product', 'منتج'), ('entity', 'جهة'),
        ('community_post', 'منشور مجتمعي'), ('comment', 'تعليق'),
    ]
    STATUS_CHOICES = [('pending', 'قيد المراجعة'), ('resolved', 'تم الحل')]
    # نوع البلاغ — يحدد إذا كان مرتبط بمنتج/جهة معيّنة، أو بلاغ عام
    # (مشكلة تقنية بالتطبيق، اقتراح تحسين، أو أي شيء ثاني)
    CATEGORY_CHOICES = [
        ('data_error', 'خطأ في بيانات منتج/جهة'),
        ('app_bug', 'مشكلة تقنية بالتطبيق'),
        ('other', 'أخرى'),
    ]

    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='data_error')

    # اختياريان الآن — البلاغ العام (تقني/أخرى) ما يحتاج يكون مرتبط
    # بمنتج أو جهة معيّنة أصلاً
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, null=True, blank=True)
    target_id = models.IntegerField(null=True, blank=True)

    # اسم المنتج/الجهة وقت الإبلاغ — يُحفظ من التطبيق مباشرة، حتى ما
    # تحتاج لوحة التحكم تبحث عن المنتج يدويًا بس عشان تعرف اسمه
    target_name = models.CharField(max_length=255, blank=True, default='')

    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(
    'users.User', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.target_type:
            return f"{self.target_type} - {self.status}"
        return f"بلاغ عام ({self.get_category_display()}) - {self.status}"
