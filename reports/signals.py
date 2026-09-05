from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Report

# عدد المُبلِّغين المختلفين اللي يشغّل الإخفاء التلقائي — راجع
# community/points.py TRUST_AUTO_PUBLISH_THRESHOLD للسياق الكامل: هذا
# هو "خط الدفاع الثاني" (مراجعة تفاعلية بعد النشر) اللي يعوّض عن رفع
# النشر التلقائي للمستخدمين الموثوقين. 3 مستخدمين مختلفين حد معقول:
# كافٍ يمنع بلاغ فردي كيدي واحد من إخفاء محتوى سليم، وقليل بما يكفي
# يحمي من انتشار محتوى فعلاً مخالف قبل ما يوصله أدمن
REPORT_AUTO_HIDE_THRESHOLD = 3


@receiver(post_save, sender='reports.Report')
def award_points_on_resolution(sender, instance, **kwargs):
    """نفس منطق suggestions/signals.py بالضبط — راجع تعليقه للتفصيل."""
    if instance.status != 'resolved':
        return
    from community.points import award_points
    award_points(
        instance.user, 'report_resolved',
        reference_type='report', reference_id=instance.id,
    )


@receiver(post_save, sender='reports.Report')
def auto_hide_on_reports_threshold(sender, instance, created, **kwargs):
    """
    إخفاء تلقائي (status='hidden') لمنشور/تعليق وصل لعتبة بلاغات من
    مستخدمين مختلفين — مو مجرد عدد بلاغات (لمنع حساب واحد يبلّغ عدة
    مرات صوريًا). .update() بدل .save() عمدًا: أسرع ولا يُطلق أي signal
    ثانٍ (النقاط لا علاقة لها بحدث "إخفاء"، فما نحتاج نمر بمسار save
    الكامل). الفلترة على الحالة الحالية تمنع "إعادة إخفاء" منشور
    الأدمن خلّاه منشورًا عمدًا بعد ما راجعه فعليًا ووجده سليم.
    """
    if not created or instance.target_type not in ('community_post', 'comment', 'review'):
        return
    distinct_reporters = Report.objects.filter(
        target_type=instance.target_type, target_id=instance.target_id,
    ).values('user').distinct().count()
    if distinct_reporters < REPORT_AUTO_HIDE_THRESHOLD:
        return

    if instance.target_type == 'community_post':
        from posts.models import CommunityPost
        CommunityPost.objects.filter(id=instance.target_id, status='published').update(status='hidden')
    elif instance.target_type == 'comment':
        from posts.models import Comment
        Comment.objects.filter(id=instance.target_id, status='visible').update(status='hidden')
    else:
        from reviews.models import Review
        Review.objects.filter(id=instance.target_id, status='visible').update(status='hidden')
