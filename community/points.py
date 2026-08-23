"""
حساب النقاط — مقصود إنه دايمًا ديناميكي (بدون حقل points مخزَّن على
User)، عشان ما يصير تزامن خاطئ بين النقاط المعروضة والأفعال الفعلية.

مصادر النقاط الثلاثة الحالية، وليش أوزانها مختلفة:
- اقتراح مقبول (10): يمر بمراجعة بشرية فعلية قبل ما يُحتسب — أعلى وزن.
- بلاغ محلول (5): يمر بمراجعة بشرية أيضًا، لكن جهد أقل من اقتراح.
- منتج مميّز تم مسحه (1): وزن منخفض عمدًا. صحيح إن السيرفر يتحقق الآن
  من وجود المنتج فعليًا بقاعدتنا (راجع scans/views.py — barcode
  lookup سيرفري، ما نثق بأي شيء يرسله العميل عن هوية المنتج)، لكن هذا
  التحقق لا يثبت إن مسحًا فعليًا حصل بالكاميرا — أي حد يعرف باركود
  منتج حقيقي (والباركودات أصلًا معلومة للعموم، مو سرية) يقدر يستدعي
  endpoint المزامنة مباشرة بدون فتح التطبيق إطلاقًا. هذا خطر متبقٍّ
  حقيقي وواعٍ، مو سهو، ولهذا وزنه صغير جدًا مقارنة بالمصدرين الآخرين.
"""
from django.db.models import Count, F, IntegerField, Q, ExpressionWrapper
from suggestions.models import Suggestion
from reports.models import Report
from scans.models import ScanHistory

SUGGESTION_APPROVED_POINTS = 10
REPORT_RESOLVED_POINTS = 5
SCAN_DISTINCT_PRODUCT_POINTS = 1


def calculate_points(user):
    """نقاط مستخدم واحد — يكفي لصفحة "حسابي"."""
    approved_suggestions = Suggestion.objects.filter(user=user, status='approved').count()
    resolved_reports = Report.objects.filter(user=user, status='resolved').count()
    # منتجات مميّزة (distinct) بس — مسح نفس المنتج 100 مرة يساوي مسحه
    # مرة وحدة بالنقاط، عشان نمنع أبسط شكل تلاعب (تكرار نفس الباركود)
    distinct_products_scanned = (
        ScanHistory.objects.filter(user=user, found=True, product__isnull=False)
        .values('product').distinct().count()
    )
    return (
        approved_suggestions * SUGGESTION_APPROVED_POINTS
        + resolved_reports * REPORT_RESOLVED_POINTS
        + distinct_products_scanned * SCAN_DISTINCT_PRODUCT_POINTS
    )


def annotate_points(user_queryset):
    """
    يضيف حقل points لكل عنصر بقائمة مستخدمين — استعلام SQL واحد فعّال
    بدل استدعاء calculate_points() لكل مستخدم لحاله (أساسي للترتيب
    العام حتى يشتغل ORDER BY على مستوى قاعدة البيانات، مو Python).

    distinct=True على الثلاثة Count كلها لازم: بما إن الاستعلام فيه
    JOIN لثلاث علاقات عكسية مختلفة (suggestion، report، scan_history)
    بنفس الوقت، بدون distinct=True الأرقام تتضاعف فعليًا بسبب تعدد
    نتائج الـ JOIN (fan-out) — تحققت من هذا فعليًا بالاختبار، مو افتراض.
    """
    return user_queryset.annotate(
        approved_suggestions=Count(
            'suggestion', filter=Q(suggestion__status='approved'), distinct=True
        ),
        resolved_reports=Count(
            'report', filter=Q(report__status='resolved'), distinct=True
        ),
        distinct_products_scanned=Count(
            'scan_history__product',
            filter=Q(scan_history__found=True, scan_history__product__isnull=False),
            distinct=True,
        ),
    ).annotate(
        points=ExpressionWrapper(
            F('approved_suggestions') * SUGGESTION_APPROVED_POINTS
            + F('resolved_reports') * REPORT_RESOLVED_POINTS
            + F('distinct_products_scanned') * SCAN_DISTINCT_PRODUCT_POINTS,
            output_field=IntegerField(),
        ),
    )
