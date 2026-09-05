"""
حساب النقاط — لسا ديناميكي دايمًا (بدون حقل points مخزَّن على User)،
لكن بدل إعادة حساب من 3 جداول مختلفة بمنطق مبعثر، المصدر الوحيد الآن
هو PointTransaction (سجل أحداث، راجع community/models.py للتفصيل).

هذا الملف هو المكان الوحيد اللي يحدّد "كم نقطة لكل فعل" — أي تغيير
بوزن مستقبلًا يصير هنا فقط، بدون MIGRATION.
"""
from django.db.models import Sum, IntegerField
from django.db.models.functions import Coalesce
from .models import PointTransaction

POINTS_WEIGHTS = {
    # مراجَعة بشرية فعلية قبل الاحتساب — أعلى وزن
    'suggestion_approved': 10,
    # مراجَعة بشرية أيضًا، جهد أقل من اقتراح
    'report_resolved': 5,
    # وزن منخفض عمدًا في نسخة سابقة من هذا الملف (كنا لا نثق أن المسح تم
    # فعليًا بالكاميرا). رُفع الآن لـ 3 — التحقق من صحة الباركود سيرفريًا
    # (found=True فقط يُحتسب) كافٍ لمنح وزن أعلى قليلاً، والمسح يبقى
    # الفعل الأخف مقارنة باقتراح/بلاغ تمت مراجعته فعليًا
    'distinct_product_scanned': 3,
    # منشور مجتمعي مرّ بمراجعة إدارية ونُشر — أخف من اقتراح (مراجعة
    # أبسط)، أثقل من مسح (محتوى فعلي أنتجه المستخدم)
    'post_published': 3,
    # تعليق اختاره صاحب السؤال كأفضل إجابة — قيمة معرفية محقَّقة من
    # طرف آخر (مو من الإدارة)، نفس وزن البلاغ المحلول
    'comment_best_answer': 5,
    # نقطة واحدة فقط لكل تفاعل "مفيد" فريد تستلمه — العائق الطبيعي هنا
    # هو unique_together(user, post) على PostReaction نفسه: التلاعب
    # يحتاج فعليًا عدة حسابات مستخدمين حقيقية مختلفة، مو حسابًا واحدًا
    # يكرر التفاعل، فما احتجنا سقف يومي إضافي فوق هذا
    'post_reaction_received': 1,
    'comment_reaction_received': 1,
}


def award_points(user, action, reference_type='', reference_id=None):
    """
    يمنح نقاط لفعل معيّن — يُستدعى من الـ signals (راجع posts/signals.py،
    suggestions/signals.py، reports/signals.py، scans/signals.py).

    get_or_create يعتمد على unique_together بالموديل نفسه، فاستدعاء
    هذي الدالة أكثر من مرة لنفس الحدث (مثلًا save() انطلقت مرتين
    بالخطأ لسجلّة بنفس الحالة) لا يضاعف النقاط — آمنة للاستدعاء
    بدون شرط "هل تغيّرت الحالة فعليًا؟" بالـ signal نفسه.
    """
    if user is None:
        return None
    points = POINTS_WEIGHTS.get(action)
    if points is None:
        raise ValueError(f'وزن نقاط غير معرّف للفعل: {action}')
    transaction, _created = PointTransaction.objects.get_or_create(
        user=user,
        action=action,
        reference_type=reference_type,
        reference_id=reference_id,
        defaults={'points': points},
    )
    return transaction


def revoke_points(user, action, reference_type='', reference_id=None):
    """يسحب نقاط حدث معيّن — يُستدعى عند إلغاء تفاعل (unlike) مثلًا."""
    PointTransaction.objects.filter(
        user=user, action=action, reference_type=reference_type, reference_id=reference_id,
    ).delete()


def calculate_points(user):
    """نقاط مستخدم واحد — يكفي لصفحة "حسابي"."""
    total = PointTransaction.objects.filter(user=user).aggregate(
        total=Coalesce(Sum('points'), 0, output_field=IntegerField())
    )['total']
    return total


def annotate_points(user_queryset):
    """
    يضيف حقل points لكل عنصر بقائمة مستخدمين — استعلام SQL واحد فعّال
    (تجميع من جدول واحد PointTransaction بدل عدة JOIN على جداول
    مختلفة كما كان بالنسخة القديمة)، أساسي لقائمة الصدارة (أفضل 1000)
    حتى يشتغل الترتيب على مستوى قاعدة البيانات، مو Python.
    """
    return user_queryset.annotate(
        points=Coalesce(
            Sum('point_transactions__points'), 0, output_field=IntegerField()
        ),
    )


LEVEL_THRESHOLDS = [
    (500, 'سفير بصيرة'),
    (300, 'مساهم موثوق'),
    (150, 'مساهم نشط'),
    (50, 'مساهم'),
    (0, 'مبتدئ'),
]

# نشر تلقائي بدون مراجعة أدمن — يطابق عتبة مستوى "مساهم" أعلاه عمدًا
# (نفس الرقم، مو صدفة): مستخدم أثبت مصداقية كافية (اقتراحات مقبولة/
# بلاغات صحيحة/مسح) يستاهل نشرًا فوريًا لمحتواه، بدل ما يُعامل بنفس
# حذر حساب جديد بلا سجل. هذا هو الحل الوحيد الواقعي لمشكلة "المراجعة
# المسبقة لا تتوسّع مع نمو عدد المستخدمين" — الحماية البديلة (راجع
# reports/signals.py) هي مراجعة تفاعلية بعد النشر (بلاغات)، مو قبله
TRUST_AUTO_PUBLISH_THRESHOLD = 50


def is_trusted_contributor(user):
    """مستخدم منشوره يُنشر فورًا بدون انتظار مراجعة أدمن. راجع التعليق أعلى TRUST_AUTO_PUBLISH_THRESHOLD."""
    return calculate_points(user) >= TRUST_AUTO_PUBLISH_THRESHOLD


def get_level(points):
    """
    مستوى نصي مشتق من النقاط — محسوب ديناميكيًا دائمًا (نفس مبدأ
    contributor_reputation بـ posts/reputation.py)، بدون أي جدول أو
    حقل إضافي لتخزينه.
    """
    for threshold, label in LEVEL_THRESHOLDS:
        if points >= threshold:
            return label
    return LEVEL_THRESHOLDS[-1][1]
