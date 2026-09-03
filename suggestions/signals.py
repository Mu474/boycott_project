from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='suggestions.Suggestion')
def award_points_on_approval(sender, instance, **kwargs):
    """
    نمنح النقاط عند كل save() تكون فيه الحالة 'approved' — بدون شرط
    "هل تغيّرت الحالة الآن فعليًا؟" لأن award_points نفسها idempotent
    (get_or_create على unique_together)، فما فيه خطر تكرار النقاط لو
    انطلق الـ signal أكثر من مرة لنفس السجلّة المعتمدة.
    """
    if instance.status != 'approved':
        return
    from community.points import award_points
    award_points(
        instance.user, 'suggestion_approved',
        reference_type='suggestion', reference_id=instance.id,
    )
