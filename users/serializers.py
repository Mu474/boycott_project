from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'username', 'is_staff', 'is_superuser', 'created_at']


class MeSerializer(serializers.ModelSerializer):
    """
    الملف الشخصي للمستخدم الحالي — يشمل النقاط (محسوبة ديناميكيًا،
    راجع community/points.py لتفاصيل ليش مو حقل مخزَّن)، والمستوى
    المشتق منها، وثلاث إحصائيات مساهمة (مسح/اقتراحات مقبولة/بلاغات
    مقبولة) تُعرض بشاشة "حسابي" بنفس شكل بطاقات "مسؤوليتي".
    """
    points = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    scans_count = serializers.SerializerMethodField()
    suggestions_approved_count = serializers.SerializerMethodField()
    reports_resolved_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'username', 'is_staff', 'points', 'level',
            'scans_count', 'suggestions_approved_count', 'reports_resolved_count', 'created_at',
        ]

    def get_points(self, obj):
        from community.points import calculate_points
        return calculate_points(obj)

    def get_level(self, obj):
        from community.points import calculate_points, get_level
        return get_level(calculate_points(obj))

    def get_scans_count(self, obj):
        # منتجات مختلفة تم مسحها — نفس التعريف اللي يمنح النقاط
        # (distinct_product_scanned بـ community/points.py)، مو عدد
        # عمليات المسح الخام (لو مسح نفس المنتج 20 مرة يبقى يُحسب مرة
        # وحدة هنا)، حتى يتطابق الرقم المعروض مع مصدر نقاطه الفعلي
        from scans.models import ScanHistory
        return ScanHistory.objects.filter(user=obj, found=True, product__isnull=False).values('product').distinct().count()

    def get_suggestions_approved_count(self, obj):
        from suggestions.models import Suggestion
        return Suggestion.objects.filter(user=obj, status='approved').count()

    def get_reports_resolved_count(self, obj):
        from reports.models import Report
        return Report.objects.filter(user=obj, status='resolved').count()
