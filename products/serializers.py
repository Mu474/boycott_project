from rest_framework import serializers
from .models import Product
from entities.serializers import EntityMinimalSerializer
from categories.serializers import CategorySerializer


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'barcode',
            'status', 'reason', 'evidence_url',
            'category', 'entity', 'created_at'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    entity = EntityMinimalSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    # ملخّص التقييمات (نظام reviews المنفصل عن تجارب المجتمع) — يُحسب
    # ديناميكيًا دائمًا (نفس مبدأ النقاط)، None لو ما فيه تقييمات بعد
    # (مو 0 — فرق مهم بالواجهة بين "لا يوجد تقييم" و"معدّل التقييم صفر")
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'barcode',
            'status', 'reason', 'evidence_url',
            'category', 'entity', 'average_rating', 'review_count', 'created_at'
        ]

    def get_average_rating(self, obj):
        from django.db.models import Avg
        result = obj.reviews.filter(status='visible').aggregate(avg=Avg('rating'))['avg']
        return round(result, 1) if result is not None else None

    def get_review_count(self, obj):
        return obj.reviews.filter(status='visible').count()