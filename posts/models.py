from django.db import models
from users.models import User
from products.models import Product
from entities.models import BusinessEntity


class CommunityPost(models.Model):
    """
    محتوى مجتمعي — 4 أنواع فقط (قرار مدروس، مو نقص): باقي "أنواع
    المساهمة" المذكورة بالنقاش (اقتراح منتج، بلاغ خطأ) أصلًا لها بيت
    صحيح موجود (Suggestion، Report على التوالي)، وحشرها هنا كان يخلق
    مسارَي مراجعة مزدوجين بلا داعٍ.

    التوسعة الأخيرة أضافت نوعين لتغطية احتياجين حقيقيين ما كانا
    مغطّيين: "أبحث عن بديل" (seeking_alternative) و"سؤال" (question).
    لم نضف "نصيحة" لأنها تتداخل عمليًا مع info (فرق عرض فقط، مو نوع
    محتوى مختلف)، ولا "مقارنة" لأنها تحتاج ربط بمنتجين مو منتج واحد —
    تغيير بنية الموديل نفسه، أُجّل لمرحلة لاحقة بدل تعديل جذري الآن.
    """
    TYPE_CHOICES = [
        ('experience', 'تجربة مع منتج/بديل'),
        ('info', 'معلومة توعوية'),
        ('seeking_alternative', 'أبحث عن بديل'),
        ('question', 'سؤال'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('published', 'منشور'),
        ('hidden', 'مخفي'),
        ('rejected', 'مرفوض'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_posts')
    post_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
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


class Comment(models.Model):
    """
    تعليق على منشور مجتمعي — جدول واحد بس لكل من التعليقات والردود،
    عبر parent_comment ذاتي المرجع (self-referencing)، بدل جدول Reply
    منفصل. NULL يعني تعليق أساسي مباشر على المنشور، وأي قيمة تعني رد
    على تعليق آخر. عمدًا بلا تداخل لا نهائي بالواجهة (رد على رد) —
    نفس فلسفة "نوعان بس" بالمنشورات: مستوى واحد من الردود يكفي تمامًا
    لمشروع بهذا الحجم، وأي تعمّق أكثر يعقّد الواجهة بلا فائدة حقيقية.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    parent_comment = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies'
    )
    body = models.CharField(max_length=500)

    # يُفعَّل فقط لو post.post_type == 'question'، ومن صاحب المنشور
    # نفسه فقط (يُفرض بمنطق العرض/السيريلايزر، مو بقيد قاعدة بيانات —
    # نفس نمط التحقق الموجود أصلًا بمنشور 'experience' اللي يفرض ربط
    # منتج/جهة بالسيريلايزر مو بالموديل). واحد بحد أقصى لكل منشور
    # (يُفرض أيضًا بالـ view: أي تفعيل جديد يلغي القديم تلقائيًا).
    is_best_answer = models.BooleanField(default=False)

    status = models.CharField(
        max_length=10,
        choices=[('visible', 'ظاهر'), ('hidden', 'مخفي')],
        default='visible',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user} على {self.post_id}'


class CommentReaction(models.Model):
    """نفس نمط PostReaction بالضبط — تفاعل 'مفيد' واحد، مو نظام متعدد."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_reactions')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')


class PostBookmark(models.Model):
    """حفظ منشور للرجوع له لاحقًا — نفس فكرة Favorites الموجودة للمنتجات، لكن للمنشورات."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_bookmarks')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='bookmarks')
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
