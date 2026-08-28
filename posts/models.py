from django.db import models
from users.models import User
from products.models import Product
from entities.models import BusinessEntity


class CommunityPost(models.Model):
    """
    محتوى مجتمعي مقصود يكون ضيّقًا بنوعين بس — قرار مدروس، مو نقص:
    باقي "أنواع المساهمة" المذكورة بالنقاش (اقتراح منتج، بلاغ خطأ)
    أصلًا لها بيت صحيح موجود (Suggestion، Report على التوالي)، وحشرها
    هنا كان يخلق مسارَي مراجعة مزدوجين بلا داعٍ.
    """
    TYPE_CHOICES = [
        ('experience', 'تجربة مع منتج/بديل'),
        ('info', 'معلومة توعوية'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('published', 'منشور'),
        ('hidden', 'مخفي'),
        ('rejected', 'مرفوض'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_posts')
    post_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    title = models.CharField(max_length=100)
    # حد أقصى صارم (500 حرف) — قرار مقصود يمنع تحوّل المنشور لمقالة
    # طويلة أو نقاش مفتوح؛ التطبيق عنده "المقالات" لمحتوى أطول أصلًا
    body = models.CharField(max_length=500)

    # منشور "تجربة" لازم يرتبط بمنتج أو جهة (يُفرض بالسيريلايزر) —
    # مبدأ "كل محتوى مرتبط بكيان بالنظام"، مو منشور عائم بلا سياق.
    # منشور "معلومة توعوية" الارتباط فيه اختياري (ممكن يكون عام، مثل
    # شرح كيفية قراءة الباركود)
    linked_product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name='community_posts'
    )
    linked_entity = models.ForeignKey(
        BusinessEntity, null=True, blank=True, on_delete=models.SET_NULL, related_name='community_posts'
    )

    image = models.ImageField(upload_to='community/', null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    # وقت النشر الفعلي (مختلف عن created_at — قد يمر وقت بينهما أثناء
    # المراجعة) — يفيد لاحقًا لأي ترتيب/تحليل يعتمد على "متى صار مرئيًا"
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_post_type_display()} - {self.title}'


class PostReaction(models.Model):
    """
    تفاعل واحد بس ('مفيد') — عمدًا، مو نظام تفاعلات متعدد (إعجاب/حب/
    إلخ). unique_together يمنع تفاعل مكرر من نفس المستخدم، ويسمح
    بـ toggle بسيط (تفاعل/إلغاء تفاعل) من نفس الـ endpoint.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reactions')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='reactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class AlternativeSuggestion(models.Model):
    """
    اقتراح "هذا المنتج بديل جيد لذاك" — بيانات مهيكلة (منتجان
    مرتبطان)، مو نص حر، فمكانها الصحيح موديل علائقي صغير مخصّص، مو
    CommunityPost ولا Suggestion (لأنها ما تُنشئ سجلًا جديدًا، بل
    تربط سجلَّين موجودين أصلًا).
    """
    STATUS_CHOICES = [('pending', 'قيد المراجعة'), ('approved', 'مقبول'), ('rejected', 'مرفوض')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='alternative_suggestions_as_source'
    )
    suggested_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='alternative_suggestions_as_target'
    )
    note = models.CharField(max_length=300, blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.source_product_id} → {self.suggested_product_id} ({self.status})'
