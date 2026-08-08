from rest_framework import serializers
from .models import BusinessEntity
from categories.serializers import CategorySerializer


class EntityMinimalSerializer(serializers.ModelSerializer):
    """نسخة مختصرة من الجهة، تُستخدم داخل المنتجات والجهات التابعة"""
    class Meta:
        model = BusinessEntity
        fields = ['id', 'name', 'logo', 'status']


class EntitySerializer(serializers.ModelSerializer):
    """تُستخدم عند الإنشاء والتعديل (POST/PUT) — حقول مسطّحة (IDs مباشرة)"""
    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'logo', 'status', 'reason',
            'evidence_url', 'category', 'parent_entity', 'created_at'
        ]


class EntityDetailSerializer(serializers.ModelSerializer):
    """تُستخدم عند العرض (GET) — التصنيف والجهة المالكة متداخلان بالاسم الكامل"""
    category = CategorySerializer(read_only=True)
    parent_entity = EntityMinimalSerializer(read_only=True)

    class Meta:
        model = BusinessEntity
        fields = [
            'id', 'name', 'logo', 'status', 'reason',
            'evidence_url', 'category', 'parent_entity', 'created_at'
        ]