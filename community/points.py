"""
حساب النقاط — مقصود إنه دايمًا ديناميكي (بدون حقل points مخزَّن على
User)، عشان ما يصير تزامن خاطئ بين النقاط المعروضة والأفعال الفعلية.
مصدرا النقاط الحاليان محدودان عمدًا لأفعال يتحقق منها السيرفر فعليًا
(اقتراح تمت الموافقة عليه، بلاغ تم حله) — مو أي فعل محلي قابل للتلاعب
(زي عدد مرات المسح، اللي لسّا ما عنده نظام يمنع تزوير الرقم من قبل
العميل حتى بعد مزامنة سجل المسح، لأن العميل يقدر يرسل سجلات وهمية
بأعداد كبيرة). لو أضفنا لاحقًا نقاط على المسح، لازم أول نضيف حماية ضد
هذا (حد أقصى يومي، أو ربط النقاط بمنتجات موجودة فعليًا بقاعدة البيانات
فقط، لا الباركودات العشوائية).

الأوزان أرقام ثابتة بمكان واحد — تغييرها هنا يغيّر كل الحسابات فورًا
بدون أي migration أو تحديث بيانات.
"""
from django.db.models import Count, F, IntegerField, Q, ExpressionWrapper
from suggestions.models import Suggestion
from reports.models import Report

SUGGESTION_APPROVED_POINTS = 10
REPORT_RESOLVED_POINTS = 5


def calculate_points(user):
    """نقاط مستخدم واحد — استعلامان بسيطان، تكفي لصفحة "حسابي"."""
    approved_suggestions = Suggestion.objects.filter(user=user, status='approved').count()
    resolved_reports = Report.objects.filter(user=user, status='resolved').count()
    return approved_suggestions * SUGGESTION_APPROVED_POINTS + resolved_reports * REPORT_RESOLVED_POINTS


def annotate_points(user_queryset):
    """
    يضيف حقل points لكل عنصر بقائمة مستخدمين — استعلام SQL واحد فعّال
    بدل استدعاء calculate_points() لكل مستخدم لحاله (أساسي للترتيب
    العام حتى يشتغل ORDER BY على مستوى قاعدة البيانات، مو Python).

    distinct=True لازم هنا: لو الـ queryset فيه أي join إضافي لاحقًا
    (مثلاً فلترة بعضوية مجموعة)، بدونه الأرقام تتضاعف بسبب الـ JOIN.
    """
    return user_queryset.annotate(
        approved_suggestions=Count(
            'suggestion', filter=Q(suggestion__status='approved'), distinct=True
        ),
        resolved_reports=Count(
            'report', filter=Q(report__status='resolved'), distinct=True
        ),
    ).annotate(
        points=ExpressionWrapper(
            F('approved_suggestions') * SUGGESTION_APPROVED_POINTS
            + F('resolved_reports') * REPORT_RESOLVED_POINTS,
            output_field=IntegerField(),
        ),
    )
