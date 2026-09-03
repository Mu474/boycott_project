from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='scans.ScanHistory')
def award_points_on_distinct_scan(sender, instance, created, **kwargs):
    """
    reference_type='product' + reference_id=product.id (مو سجلّة
    المسح نفسها) — هذا هو ما يحقّق "منتج مميّز بس" فعليًا: مسح نفس
    المنتج 100 مرة يولّد 100 سجلّة ScanHistory، لكن get_or_create على
    unique_together(user, action, reference_type, reference_id) بـ
    award_points يمنع إنشاء أكثر من PointTransaction واحدة لنفس
    المنتج لنفس المستخدم، بغض النظر عن عدد مرات المسح الفعلية.
    """
    if not created or not instance.found or not instance.product_id:
        return
    from community.points import award_points
    award_points(
        instance.user, 'distinct_product_scanned',
        reference_type='product', reference_id=instance.product_id,
    )
