from rest_framework import serializers
from .models import CommunityPost, PostReaction, AlternativeSuggestion
from users.models import User


class PostUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username']


class CommunityPostSerializer(serializers.ModelSerializer):
    user = PostUserSerializer(read_only=True)
    linked_product_name = serializers.CharField(source='linked_product.name', read_only=True, default=None)
    linked_entity_name = serializers.CharField(source='linked_entity.name', read_only=True, default=None)
    helpful_count = serializers.SerializerMethodField()
    is_reacted = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            'id', 'user', 'post_type', 'title', 'body',
            'linked_product', 'linked_product_name', 'linked_entity', 'linked_entity_name',
            'image', 'status', 'rejection_reason', 'helpful_count', 'is_reacted', 'created_at',
        ]
        read_only_fields = ['status', 'rejection_reason', 'created_at']

    def get_helpful_count(self, obj):
        # obj.reactions.count() يعمل صح حتى لو annotate صار بالـ view
        # (Count منفصل)، لكن لو الـ view زوّد annotate باسم مختلف نقدر
        # نستخدمه هنا لتفادي استعلام إضافي لكل عنصر — نتحقق أولًا
        if hasattr(obj, 'reaction_count'):
            return obj.reaction_count
        return obj.reactions.count()

    def get_is_reacted(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.reactions.filter(user=request.user).exists()

    def validate(self, data):
        post_type = data.get('post_type')
        linked_product = data.get('linked_product')
        linked_entity = data.get('linked_entity')
        if post_type == 'experience' and not linked_product and not linked_entity:
            raise serializers.ValidationError(
                {'linked_product': 'منشور التجربة لازم يرتبط بمنتج أو جهة تجارية'}
            )
        return data


class CommunityPostReviewSerializer(serializers.ModelSerializer):
    """للأدمن فقط — تحديث الحالة وسبب الرفض."""
    class Meta:
        model = CommunityPost
        fields = ['status', 'rejection_reason']


class AlternativeSuggestionSerializer(serializers.ModelSerializer):
    user = PostUserSerializer(read_only=True)
    source_product_name = serializers.CharField(source='source_product.name', read_only=True)
    suggested_product_name = serializers.CharField(source='suggested_product.name', read_only=True)

    class Meta:
        model = AlternativeSuggestion
        fields = [
            'id', 'user', 'source_product', 'source_product_name',
            'suggested_product', 'suggested_product_name', 'note',
            'status', 'rejection_reason', 'created_at',
        ]
        read_only_fields = ['status', 'rejection_reason', 'created_at']

    def validate(self, data):
        source = data.get('source_product') or getattr(self.instance, 'source_product', None)
        suggested = data.get('suggested_product') or getattr(self.instance, 'suggested_product', None)
        if source and suggested and source.id == suggested.id:
            raise serializers.ValidationError({'suggested_product': 'لا يمكن اقتراح نفس المنتج كبديل لنفسه'})
        return data


class AlternativeSuggestionReviewSerializer(serializers.ModelSerializer):
    """
    للأدمن فقط — مختلف عمدًا عن AlternativeSuggestionSerializer العادي.
    نفس الدرس اللي تعلمناه سابقًا مع Suggestion بالضبط: سيريلايزر
    الإنشاء يحمي status كـ read_only (المستخدم العادي ما يقدر يحدّدها)،
    فلو استخدمناه نفسه لمسار المراجعة، الأدمن ما يقدر يغيّر الحالة
    إطلاقًا — لازم سيريلايزر منفصل فيه status/rejection_reason قابلين
    للكتابة صراحة.
    """
    class Meta:
        model = AlternativeSuggestion
        fields = ['status', 'rejection_reason']
