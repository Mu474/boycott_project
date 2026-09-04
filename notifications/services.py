"""
دوال إنشاء الإشعارات — منطق النص والمحتوى بمكان واحد بدل ما يتكرر
جوّا views.py لتطبيقَين مختلفين (suggestions و reports). أي تعديل
لصياغة الإشعارات مستقبلًا يصير هنا بس.
"""
from .models import Notification


def _target_label(target_type):
    return {'product': 'منتج', 'entity': 'جهة تجارية'}.get(target_type, 'عنصر')


def notify_suggestion_reviewed(suggestion):
    """
    يُستدعى بعد ما تتغيّر حالة اقتراح فعليًا لـ approved أو rejected —
    المسؤولية على المستدعي (suggestions/views.py) يتحقق إن الحالة
    تغيّرت فعلًا قبل الاستدعاء، عشان ما نكرر نفس الإشعار لو الأدمن حدّث
    حقل ثاني بالاقتراح بدون تغيير الحالة نفسها.
    """
    if suggestion.status == 'approved':
        Notification.objects.create(
            user=suggestion.user,
            notification_type='suggestion_approved',
            title='تمت الموافقة على اقتراحك 🎉',
            body=f'اقتراحك بخصوص {_target_label(suggestion.target_type)} تمت الموافقة عليه، وحصلت على نقاط مساهمة.',
            related_id=suggestion.id,
        )
    elif suggestion.status == 'rejected':
        reason = (suggestion.rejection_reason or '').strip()
        body = f'تم رفض اقتراحك بخصوص {_target_label(suggestion.target_type)}.'
        if reason:
            body += f' السبب: {reason}'
        Notification.objects.create(
            user=suggestion.user,
            notification_type='suggestion_rejected',
            title='تم رفض اقتراحك',
            body=body,
            related_id=suggestion.id,
        )


def notify_report_resolved(report):
    """يُستدعى بعد ما تتغيّر حالة بلاغ فعليًا لـ resolved (نفس شرط التغيير الفعلي أعلاه)."""
    Notification.objects.create(
        user=report.user,
        notification_type='report_resolved',
        title='تم حل بلاغك ✅',
        body='بلاغك تمت مراجعته وحلّه، وحصلت على نقاط مساهمة.',
        related_id=report.id,
    )


def notify_post_reviewed(post):
    """يُستدعى بعد ما تتغيّر حالة منشور مجتمعي فعليًا لـ published أو rejected."""
    if post.status == 'published':
        Notification.objects.create(
            user=post.user,
            notification_type='post_published',
            title='تم نشر مساهمتك 🎉',
            body=f'منشورك "{post.title}" صار ظاهر بموجز المجتمع.',
            related_id=post.id,
        )
    elif post.status == 'rejected':
        reason = (post.rejection_reason or '').strip()
        body = f'منشورك "{post.title}" ما تمت الموافقة عليه.'
        if reason:
            body += f' السبب: {reason}'
        Notification.objects.create(
            user=post.user,
            notification_type='post_rejected',
            title='لم تتم الموافقة على منشورك',
            body=body,
            related_id=post.id,
        )


def notify_new_comment(comment):
    """
    يُستدعى عند إنشاء تعليق جديد (posts/signals.py) — نوعان مختلفان
    حسب كون التعليق أساسي أو رد:
    - تعليق أساسي (parent_comment=None) → إشعار لصاحب المنشور
    - رد (parent_comment موجود) → إشعار لصاحب التعليق الأب، مو صاحب
      المنشور (هو الشخص المعني فعليًا بالرد)

    ما نُشعر المستخدم بتعليقه على منشوره/رده على تعليقه هو نفسه —
    فحص user != recipient بالأسفل يمنع هذا بلا داعٍ لأي شرط إضافي
    بمكان الاستدعاء.
    """
    if comment.parent_comment_id:
        recipient = comment.parent_comment.user
        if recipient.id == comment.user_id:
            return
        Notification.objects.create(
            user=recipient,
            notification_type='comment_reply',
            title='رد جديد على تعليقك 💬',
            body=f'{comment.user.name} ردّ على تعليقك بمنشور "{comment.post.title}".',
            related_id=comment.post_id,
        )
    else:
        recipient = comment.post.user
        if recipient.id == comment.user_id:
            return
        Notification.objects.create(
            user=recipient,
            notification_type='post_comment',
            title='تعليق جديد على منشورك 💬',
            body=f'{comment.user.name} علّق على منشورك "{comment.post.title}".',
            related_id=comment.post_id,
        )
