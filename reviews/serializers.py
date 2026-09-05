from rest_framework import serializers
from .models import Review
from users.models import User


class ReviewUserSerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'level']

    def get_level(self, obj):
        from community.points import calculate_points, get_level
        return get_level(calculate_points(obj))


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)
    is_own = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'entity', 'rating', 'body', 'is_own', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_is_own(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.user_id == request.user.id

    def validate(self, data):
        product = data.get('product', getattr(self.instance, 'product', None))
        entity = data.get('entity', getattr(self.instance, 'entity', None))

        if not product and not entity:
            raise serializers.ValidationError('التقييم لازم يرتبط بمنتج أو جهة تجارية')
        if product and entity:
            raise serializers.ValidationError('التقييم يرتبط بمنتج واحد أو جهة واحدة، مو الاثنين معًا')

        target = product or entity
        if target.status == 'boycott':
            raise serializers.ValidationError('لا يمكن تقييم منتج أو جهة مصنّفة ضمن قائمة المقاطعة')

        # منع تكرار التقييم — UniqueConstraint بالموديل يحمي قاعدة
        # البيانات فعليًا، لكن بدون هذا التحقق هنا كان الخطأ يوصل
        # كـ IntegrityError عام (500) بدل رسالة واضحة للمستخدم (400)
        request = self.context.get('request')
        if request and self.instance is None:
            existing = Review.objects.filter(user=request.user)
            existing = existing.filter(product=product) if product else existing.filter(entity=entity)
            if existing.exists():
                raise serializers.ValidationError('قيّمت هذا العنصر من قبل — عدّل تقييمك الحالي بدل إضافة تقييم جديد')

        return data
