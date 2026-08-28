"""
حساب "موثوقية" المستخدم — نسبة اقتراحاته المقبولة من إجمالي المراجَع
منها (استُبعد المعلّق). محسوبة ديناميكيًا دائمًا، بدون حقل مخزَّن —
نفس مبدأ community/points.py بالضبط (تفادي أي تزامن خاطئ).

MIN_REVIEWED_FOR_REPUTATION: حماية من عيّنة صغيرة — مستخدم جديد أول
اقتراح له انرفض بالصدفة ما لازم يشوف "موثوقيتك: 0%" فورًا. نرجّع
None لحد ما يكون عنده 5 اقتراحات مراجَعة على الأقل؛ الواجهة تتعامل
مع None بعدم عرض أي رقم إطلاقًا (مو عرض 0% أو "—").
"""
from suggestions.models import Suggestion

MIN_REVIEWED_FOR_REPUTATION = 5


def contributor_reputation(user):
    reviewed = Suggestion.objects.filter(user=user).exclude(status='pending').count()
    if reviewed < MIN_REVIEWED_FOR_REPUTATION:
        return None
    approved = Suggestion.objects.filter(user=user, status='approved').count()
    return round(approved / reviewed * 100)
