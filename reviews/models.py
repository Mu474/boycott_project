from django.db import models
from django.db.models import Q
from users.models import User
from products.models import Product
from entities.models import BusinessEntity


class Review(models.Model):
    """
    تقييم + رأي على منتج أو جهة تجارية — منفصل تمامًا عن CommunityPost
    (المجتمع). الفرق الجوهري مو مجرد مكان العرض:

    - "تجربة" بالمجتمع: منشور حر (عنوان + نص طويل)، يفتح نقاشًا (تعليقات/
      ردود)، يظهر بموجز عام، وهدفه مشاركة قصة/معرفة.
    - "تقييم" هنا: رقم (1-5 نجوم) + رأي قصير اختياري، مرتبط حصرًا بمنتج/
      جهة واحدة يظهر تحتها فقط، بلا نقاش تحته، وهدفه قياس رضا المستخدمين
      بشكل مجمّع (متوسط + عدد)، أقرب لتقييمات المتاجر منه لمنشور اجتماعي.

    قيد جوهري (يُفرض بالسيريلايزر، راجع reviews/serializers.py): لا
    تقييم على منتج/جهة status='boycott' — تقييم شيء "لازم تقاطعه" لا
    معنى له (هل "3 نجوم" على منتج مقاطَع؟ السؤال نفسه غير منطقي)،
    عكس caution/alternative اللي التقييم فيها له قيمة فعلية.
    """
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    # بالضبط واحد منهم — نفس نمط CommunityPost.linked_product/linked_entity
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE, related_name='reviews')
    entity = models.ForeignKey(BusinessEntity, null=True, blank=True, on_delete=models.CASCADE, related_name='reviews')

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    # اختياري عمدًا — أحيانًا المستخدم يبي بس يعطي نجوم بدون تعليق مكتوب،
    # ما نجبره يكتب رأي طويل زي منشور المجتمع
    body = models.CharField(max_length=500, blank=True, default='')

    status = models.CharField(
        max_length=10,
        choices=[('visible', 'ظاهر'), ('hidden', 'مخفي')],
        default='visible',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # unique_together العادي ما يصلح هنا: مع حقل NULL (المنتج
            # فاضي مثلًا بتقييم جهة)، قواعد البيانات تعتبر كل NULL
            # مختلف عن غيره، فما يمنع التكرار فعليًا. UniqueConstraint
            # الشرطي (condition) هو الحل الصحيح: يفرض التفرّد بس على
            # الصفوف اللي فيها المنتج/الجهة فعليًا موجودة.
            models.UniqueConstraint(
                fields=['user', 'product'], condition=Q(product__isnull=False),
                name='unique_user_product_review',
            ),
            models.UniqueConstraint(
                fields=['user', 'entity'], condition=Q(entity__isnull=False),
                name='unique_user_entity_review',
            ),
        ]

    def __str__(self):
        target = self.product or self.entity
        return f'{self.user} → {target} ({self.rating}★)'
