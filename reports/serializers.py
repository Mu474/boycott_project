from rest_framework import serializers
from .models import Report
from users.models import User


class ReportUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class ReportSerializer(serializers.ModelSerializer):
    user = ReportUserSerializer(read_only=True)
    # صورة العنصر المُبلَّغ عنه (شعار الجهة أو صورة المنتج) — الأدمن
    # يحتاجها يشوفها بوضوح بلوحة التحكم بدل ما يبحث عن العنصر يدويًا.
    # SerializerMethodField لأن Report نفسه ما يخزّن صورة، بس مرتبط
    # بمنتج/جهة عبر target_type/target_id (مرجع بولي-مورفيك بسيط)
    target_image = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'category', 'target_type', 'target_id', 'target_name',
            'target_image', 'reason', 'status', 'user', 'reviewed_by', 'created_at'
        ]
        read_only_fields = ['status', 'reviewed_by', 'created_at']

    def get_target_image(self, obj):
        if not obj.target_type or not obj.target_id:
            return None
        try:
            if obj.target_type == 'product':
                from products.models import Product
                target = Product.objects.filter(pk=obj.target_id).first()
                image = target.image if target else None
            elif obj.target_type == 'entity':
                from entities.models import BusinessEntity
                target = BusinessEntity.objects.filter(pk=obj.target_id).first()
                image = target.logo if target else None
            else:
                return None
            return image.url if image else None
        except Exception:
            # لو انحذف العنصر الأصلي أو صار أي خطأ غير متوقع، ما نكسر
            # البلاغ كله — نرجّع بس بدون صورة
            return None


class ReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['status', 'reviewed_by']
