from rest_framework import serializers
from .models import (
    CommunityPost, PostReaction, PostBookmark, Comment, CommentReaction,
    AlternativeSuggestion,
)
from users.models import User


class PostUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username']


# أنواع المنشورات اللي تفرض ربطًا إلزاميًا بمنتج أو جهة — 'experience'
# (تجربة لازم تكون عن شيء محدد) و'seeking_alternative' (طلب بديل
# لازم يحدد المصدر اللي يبحث له عن بديل). 'info' و'question' الربط
# فيهما اختياري (ممكن يكونا عامّين، بلا سياق منتج/جهة محدد)
TYPES_REQUIRING_LINK = {'experience', 'seeking_alternative'}


class CommunityPostSerializer(serializers.ModelSerializer):
    user = PostUserSerializer(read_only=True)
    linked_product_name = serializers.CharField(source='linked_product.name', read_only=True, default=None)
    linked_entity_name = serializers.CharField(source='linked_entity.name', read_only=True, default=None)
    # روابط الصور الفعلية للمنتج/الجهة المرتبطة — قبل هذا كان يظهر
    # اسم المنتج بس كنص، وصعب على المستخدم يتعرف عليه بدون صورة
    # (Product.image وBusinessEntity.logo موجودان أصلًا بقاعدة
    # البيانات، بس ما كانا يُرسلان هنا إطلاقًا)
    linked_product_image = serializers.SerializerMethodField()
    linked_entity_image = serializers.SerializerMethodField()
    helpful_count = serializers.SerializerMethodField()
    is_reacted = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            'id', 'user', 'post_type', 'title', 'body',
            'linked_product', 'linked_product_name', 'linked_product_image',
            'linked_entity', 'linked_entity_name', 'linked_entity_image',
            'image', 'status', 'rejection_reason', 'helpful_count', 'is_reacted',
            'comment_count', 'is_bookmarked', 'created_at',
        ]
        read_only_fields = ['status', 'rejection_reason', 'created_at']

    def _absolute(self, url):
        if not url:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_linked_product_image(self, obj):
        if obj.linked_product and obj.linked_product.image:
            return self._absolute(obj.linked_product.image.url)
        return None

    def get_linked_entity_image(self, obj):
        if obj.linked_entity and obj.linked_entity.logo:
            return self._absolute(obj.linked_entity.logo.url)
        return None

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

    def get_comment_count(self, obj):
        if hasattr(obj, 'comment_count_annotated'):
            return obj.comment_count_annotated
        return obj.comments.filter(status='visible').count()

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.bookmarks.filter(user=request.user).exists()

    def validate(self, data):
        post_type = data.get('post_type')
        linked_product = data.get('linked_product')
        linked_entity = data.get('linked_entity')
        if post_type in TYPES_REQUIRING_LINK and not linked_product and not linked_entity:
            raise serializers.ValidationError(
                {'linked_product': 'هذا النوع من المنشورات لازم يرتبط بمنتج أو جهة تجارية'}
            )
        return data


class CommentSerializer(serializers.ModelSerializer):
    user = PostUserSerializer(read_only=True)
    helpful_count = serializers.SerializerMethodField()
    is_reacted = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'post', 'parent_comment', 'body',
            'is_best_answer', 'status', 'helpful_count', 'is_reacted', 'created_at',
        ]
        read_only_fields = ['status', 'is_best_answer', 'created_at']

    def get_helpful_count(self, obj):
        return obj.reactions.count()

    def get_is_reacted(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.reactions.filter(user=request.user).exists()

    def validate(self, data):
        post = data.get('post') or getattr(self.instance, 'post', None)
        parent_comment = data.get('parent_comment')
        if parent_comment and parent_comment.post_id != post.id:
            raise serializers.ValidationError({'parent_comment': 'التعليق الأب لازم يكون على نفس المنشور'})
        # مستوى واحد بس من الردود — منع رد على رد (راجع تعليق Comment بالموديل)
        if parent_comment and parent_comment.parent_comment_id is not None:
            raise serializers.ValidationError({'parent_comment': 'لا يمكن الرد على رد — رد على التعليق الأساسي فقط'})
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
