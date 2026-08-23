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
