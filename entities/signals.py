from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='entities.BusinessEntity')
def cascade_status_to_children(sender, instance, **kwargs):
    """
    عند حفظ جهة تجارية، تنتقل حالتها تلقائياً
    إلى جميع الجهات التابعة لها ومنتجاتها.
    """
    _update_children(instance)


def _update_children(entity):
    """دالة تعاودية تُحدّث جميع الأبناء والأحفاد"""

    # ── تحديث الجهات التابعة مباشرة ──────────────────────────
    # اسم الـ related_name يعتمد على تعريف الـ ForeignKey في الموديل
    # جرب: subsidiaries / children / parent_entity_set
    try:
        subsidiaries = entity.subsidiaries.all()
    except AttributeError:
        try:
            subsidiaries = entity.children.all()
        except AttributeError:
            subsidiaries = entity.__class__.objects.filter(
                parent_entity=entity
            )

    for child in subsidiaries:
        if child.status != entity.status:
            child.status = entity.status
            # نستخدم update_fields لتجنب تشغيل الـ signal مرة ثانية
            child.save(update_fields=['status'])
            # تعاودياً للأحفاد
            _update_children(child)

    # ── تحديث المنتجات التابعة لهذه الجهة ────────────────────
    try:
        products = entity.products.all()
    except AttributeError:
        try:
            from products.models import Product
            products = Product.objects.filter(entity=entity)
        except Exception:
            products = []

    for product in products:
        if product.status != entity.status:
            product.status = entity.status
            product.save(update_fields=['status'])