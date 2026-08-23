from django.db import models
from django.conf import settings
from products.models import Product


class ScanHistory(models.Model):
    """
    سجل عمليات المسح — نسخة مُزامَنة من السيرفر لسجل المسح اللي كان
    محليًا بس بتطبيق Flutter (SQLite على الجهاز، بدون أي اتصال
    بالسيرفر). الهدف الأساسي من هذا الموديل مو "شاشة سجل جديدة" —
    الشاشة أصلًا موجودة وتقرأ من القاعدة المحلية. الهدف هو توفير سجل
    يتحقق منه السيرفر عن فعل حقيقي قام به المستخدم، عشان يُبنى عليه
    لاحقًا نظام نقاط/إحصائيات لا يمكن التلاعب فيه من العميل (كان أي
    رقم "عدد مرات المسح" قبل هذا مجرد قيمة محلية غير موثوقة).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_history',
    )

    # يضمن idempotency عند المزامنة: التطبيق يولّد هذا المعرّف محليًا
    # وقت المسح نفسه (قبل أي اتصال بالسيرفر). لو انقطع الإنترنت أثناء
    # المزامنة وأعاد التطبيق المحاولة، السيرفر يتعرّف إنها نفس السجلّة
    # القديمة ولا يكرّرها.
    client_uuid = models.CharField(max_length=64, unique=True)

    barcode = models.CharField(max_length=100)
    found = models.BooleanField(default=False)

    # نربط بالمنتج الفعلي لو موجود بقاعدتنا (يفيد إحصائيات دقيقة لاحقًا)
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    # لقطة (snapshot) من اسم وحالة المنتج وقت المسح تحديدًا — لازمة لأن
    # حالة المنتج ممكن تتغيّر لاحقًا (يصير "بديل" بعد ما كان "مقاطعة"
    # مثلًا)، وأي إحصائية مستقبلية عن "قرارات المستخدم وقتها" لازم
    # تعكس الحالة وقت المسح نفسه، مو الحالة الحالية للمنتج
    product_name_snapshot = models.CharField(max_length=200, blank=True, default='')
    status_at_scan = models.CharField(max_length=11, blank=True, default='')

    # وقت المسح الفعلي بالجهاز — ممكن يكون قبل وقت وصول الطلب للسيرفر
    # بفترة طويلة، لو صار المسح وقت انقطاع الإنترنت وتمّت المزامنة لاحقًا
    scanned_at = models.DateTimeField()
    # وقت استلام السيرفر للسجلّة فعليًا (للتدقيق فقط، مو للعرض)
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['user', '-scanned_at']),
        ]
        verbose_name = 'سجل مسح'
        verbose_name_plural = 'سجلات المسح'

    def __str__(self):
        return f'{self.user} - {self.barcode} - {self.scanned_at}'
