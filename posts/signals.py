from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender='posts.CommunityPost')
def award_points_on_publish(sender, instance, **kwargs):
    """نفس منطق suggestions/signals.py — idempotent عبر award_points."""
    if instance.status != 'published':
        return
    from community.points import award_points
    award_points(
        instance.user, 'post_published',
        reference_type='post', reference_id=instance.id,
    )


@receiver(post_save, sender='posts.Comment')
def award_points_on_best_answer(sender, instance, **kwargs):
    if not instance.is_best_answer:
        return
    from community.points import award_points
    award_points(
        instance.user, 'comment_best_answer',
        reference_type='comment', reference_id=instance.id,
    )


@receiver(post_save, sender='posts.PostReaction')
def award_points_on_post_reaction(sender, instance, created, **kwargs):
    """يمنح نقطة لصاحب المنشور (مو لمن تفاعل) — reference_id=id التفاعل نفسه، يمنع تكرار الاحتساب."""
    if not created:
        return
    from community.points import award_points
    award_points(
        instance.post.user, 'post_reaction_received',
        reference_type='post_reaction', reference_id=instance.id,
    )


@receiver(post_delete, sender='posts.PostReaction')
def revoke_points_on_post_unreaction(sender, instance, **kwargs):
    """إلغاء التفاعل (toggle) يسحب النقطة المرتبطة به — نفس التناسق."""
    from community.points import revoke_points
    revoke_points(
        instance.post.user, 'post_reaction_received',
        reference_type='post_reaction', reference_id=instance.id,
    )


@receiver(post_save, sender='posts.CommentReaction')
def award_points_on_comment_reaction(sender, instance, created, **kwargs):
    if not created:
        return
    from community.points import award_points
    award_points(
        instance.comment.user, 'comment_reaction_received',
        reference_type='comment_reaction', reference_id=instance.id,
    )


@receiver(post_delete, sender='posts.CommentReaction')
def revoke_points_on_comment_unreaction(sender, instance, **kwargs):
    from community.points import revoke_points
    revoke_points(
        instance.comment.user, 'comment_reaction_received',
        reference_type='comment_reaction', reference_id=instance.id,
    )
