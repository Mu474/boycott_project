from django.db.models.signals import post_save
from django.dispatch import receiver


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
