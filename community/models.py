import secrets
import string
from django.db import models
from users.models import User


def generate_invite_code():
    """
    كود دعوة عشوائي (8 حروف/أرقام كبيرة) — طريقة الانضمام الوحيدة
    للمجموعة (لا يوجد تصفح/انضمام مباشر)، عشان يبقى معنى "مجموعتي"
    فعليًا محصور بمن شارك الرابط معهم فقط.
    """
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        if not Group.objects.filter(invite_code=code).exists():
            return code
    # احتمال شبه معدوم إحصائيًا (8 حروف/أرقام = 36^8 تركيبة)، لكن نفشل
    # بوضوح بدل ما نحفظ كود مكرر لو صار فعلًا
    raise RuntimeError('تعذّر توليد كود دعوة فريد بعد عدة محاولات')


class Group(models.Model):
    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=12, unique=True, default=generate_invite_code)
    # SET_NULL بدل CASCADE: حذف حساب المنشئ ما لازم يحذف المجموعة كلها
    # مع كل أعضائها — المجموعة تستمر بدون "منشئ" محدد
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f'{self.user} في {self.group}'


class PointTransaction(models.Model):
    """
    سجل أحداث النقاط — مو حقل points مخزَّن على User (نفس المبدأ اللي
    كان مطبّقًا بـ points.py القديم: تجنّب أي تزامن خاطئ بين رقم معروض
    ومجموع فعلي). الفرق إن القديم كان يعيد حساب المجموع من 3 جداول
    مختلفة (Suggestion، Report، ScanHistory) بمنطق مبعثر بكل استعلام؛
    هنا نُنشئ سجلًا صريحًا وقت وقوع الحدث نفسه (بالـ signal المناسب)،
    والمجموع لسا يُحسب ديناميكيًا (SUM) — نفس المبدأ، مصدر واحد أنظف،
    وأداء أفضل لقائمة الصدارة (تجميع من جدول واحد بدل عدة JOIN).

    ACTION_CHOICES تحدّد كل مصدر نقاط ممكن ووزنه — القيم الفعلية
    (الأوزان) موجودة بـ community/points.py، مو هنا، حتى تبقى قابلة
    للتعديل بمكان واحد بدون MIGRATION جديدة لكل تغيير وزن.
    """
    ACTION_CHOICES = [
        ('suggestion_approved', 'اقتراح مقبول'),
        ('report_resolved', 'بلاغ محلول'),
        ('distinct_product_scanned', 'منتج مميّز تم مسحه'),
        ('post_published', 'منشور مجتمعي نُشر'),
        ('comment_best_answer', 'تعليق اختير كأفضل إجابة'),
        ('post_reaction_received', 'تفاعل مفيد على منشورك'),
        ('comment_reaction_received', 'تفاعل مفيد على تعليقك'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    points = models.IntegerField()

    # مرجع عام (polymorphic بسيط) للسجلّة اللي سبّبت هذي المعاملة —
    # نفس نمط target_type/target_id الموجود أصلًا بـ Report، يفيد
    # لاحقًا لو احتجنا نعرض "سجل نقاطي" فيه رابط لكل حدث، أو نسحب
    # نقاط معاملة معيّنة لو اكتُشف تلاعب بمصدرها
    reference_type = models.CharField(max_length=30, blank=True, default='')
    reference_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # يمنع احتساب نفس الحدث مرتين لو انطلق الـ signal أكثر من مرة
        # بالخطأ (مثلاً save() تُستدعى مرتين بنفس الحالة) — أهم حماية
        # فعلية هنا، مو مجرد فهرسة
        unique_together = ('user', 'action', 'reference_type', 'reference_id')
        indexes = [models.Index(fields=['user'])]

    def __str__(self):
        return f'{self.user} +{self.points} ({self.action})'
