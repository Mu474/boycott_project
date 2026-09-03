from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from .models import CommunityPost, PostReaction, PostBookmark, Comment, CommentReaction, AlternativeSuggestion
from .serializers import (
    CommunityPostSerializer, CommunityPostReviewSerializer, CommentSerializer,
    AlternativeSuggestionSerializer, AlternativeSuggestionReviewSerializer,
)
from .throttles import CommunityPostRateThrottle
from notifications.services import notify_post_reviewed


class CommunityFeedView(APIView):
    """
    الموجز العام — منشورات منشورة فقط، متاح للجميع (حتى بدون تسجيل
    دخول). دعم فلترة اختيارية بـ post_type (تجربة/معلومة/طلب بديل/
    سؤال) — لو ما تحدد، يرجع كل الأنواع كما كان سابقًا.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        sort = request.query_params.get('sort', 'recent')  # recent | helpful
        post_type = request.query_params.get('post_type')
        qs = CommunityPost.objects.filter(status='published').annotate(
            reaction_count=Count('reactions', distinct=True),
            comment_count_annotated=Count('comments', filter=Q(comments__status='visible'), distinct=True),
        )
        if post_type:
            qs = qs.filter(post_type=post_type)
        qs = qs.order_by('-reaction_count', '-created_at') if sort == 'helpful' else qs.order_by('-created_at')
        serializer = CommunityPostSerializer(qs[:50], many=True, context={'request': request})
        return Response(serializer.data)


class CommunityPostCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CommunityPostRateThrottle]

    def post(self, request):
        serializer = CommunityPostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = CommunityPost.objects.filter(user=request.user)
        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


class ProductPostsView(APIView):
    """منشورات منشورة مرتبطة بمنتج معيّن — قسم "تجارب المستخدمين" بصفحة تفاصيل المنتج."""
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        posts = CommunityPost.objects.filter(status='published', linked_product_id=product_id)
        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


class PostReactionView(APIView):
    """تفاعل 'مفيد' — toggle: أول ضغطة تضيف، ثاني ضغطة تشيل."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = CommunityPost.objects.get(pk=pk, status='published')
        except CommunityPost.DoesNotExist:
            return Response({'error': 'المنشور غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        reaction = PostReaction.objects.filter(user=request.user, post=post).first()
        if reaction:
            reaction.delete()
            reacted = False
        else:
            PostReaction.objects.create(user=request.user, post=post)
            reacted = True
        return Response({'reacted': reacted, 'helpful_count': post.reactions.count()})


class PostBookmarkView(APIView):
    """حفظ/إلغاء حفظ منشور — toggle، نفس نمط PostReactionView بالضبط."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = CommunityPost.objects.get(pk=pk, status='published')
        except CommunityPost.DoesNotExist:
            return Response({'error': 'المنشور غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        bookmark = PostBookmark.objects.filter(user=request.user, post=post).first()
        if bookmark:
            bookmark.delete()
            bookmarked = False
        else:
            PostBookmark.objects.create(user=request.user, post=post)
            bookmarked = True
        return Response({'bookmarked': bookmarked})


class MyBookmarksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = CommunityPost.objects.filter(bookmarks__user=request.user).order_by('-bookmarks__created_at')
        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


# ══════════════════════════════════════════════
# التعليقات
# ══════════════════════════════════════════════
class CommentListView(APIView):
    """كل تعليقات منشور معيّن (أساسية وردود مع بعض — الترتيب الزمني
    وparent_comment كافيان للواجهة تبني الشجرة بمستوى واحد)."""
    permission_classes = [AllowAny]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id, status='visible')
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)


class CommentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CommunityPostRateThrottle]

    def post(self, request):
        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentBestAnswerView(APIView):
    """
    صاحب منشور 'question' فقط يقدر يحدد أفضل إجابة، وبحد أقصى واحد
    بكل مرة (تفعيل جديد يلغي القديم تلقائيًا — راجع تعليق is_best_answer
    بالموديل).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            comment = Comment.objects.select_related('post').get(pk=pk, status='visible')
        except Comment.DoesNotExist:
            return Response({'error': 'التعليق غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if comment.post.post_type != 'question':
            return Response({'error': 'أفضل إجابة تنطبق فقط على منشورات الأسئلة'}, status=status.HTTP_400_BAD_REQUEST)
        if comment.post.user_id != request.user.id:
            return Response({'error': 'فقط صاحب السؤال يقدر يحدد أفضل إجابة'}, status=status.HTTP_403_FORBIDDEN)

        Comment.objects.filter(post=comment.post, is_best_answer=True).update(is_best_answer=False)
        comment.is_best_answer = True
        comment.save(update_fields=['is_best_answer'])
        return Response(CommentSerializer(comment, context={'request': request}).data)


class CommentReactionView(APIView):
    """تفاعل 'مفيد' على تعليق — toggle، نفس نمط PostReactionView."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk, status='visible')
        except Comment.DoesNotExist:
            return Response({'error': 'التعليق غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        reaction = CommentReaction.objects.filter(user=request.user, comment=comment).first()
        if reaction:
            reaction.delete()
            reacted = False
        else:
            CommentReaction.objects.create(user=request.user, comment=comment)
            reacted = True
        return Response({'reacted': reacted, 'helpful_count': comment.reactions.count()})


# ══════════════════════════════════════════════
# إدارة (لوحة التحكم فقط)
# ══════════════════════════════════════════════
class CommunityPostAdminListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        posts = CommunityPost.objects.all()
        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


class CommunityPostReviewView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            post = CommunityPost.objects.get(pk=pk)
        except CommunityPost.DoesNotExist:
            return Response({'error': 'المنشور غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        previous_status = post.status
        serializer = CommunityPostReviewSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_by=request.user)
            if post.status == 'published' and post.published_at is None:
                post.published_at = timezone.now()
                post.save(update_fields=['published_at'])
            # إشعار بس لو الحالة تغيّرت فعليًا لحالة نهائية — نفس شرط
            # الاقتراحات والبلاغات بالضبط، يمنع تكرار الإشعار
            if previous_status != post.status and post.status in ('published', 'rejected'):
                notify_post_reviewed(post)
            return Response(CommunityPostSerializer(post, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════
# اقتراح بديل (منتج ← منتج)
# ══════════════════════════════════════════════
class AlternativeSuggestionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AlternativeSuggestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlternativeSuggestionListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        items = AlternativeSuggestion.objects.all()
        serializer = AlternativeSuggestionSerializer(items, many=True)
        return Response(serializer.data)


class AlternativeSuggestionReviewView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            item = AlternativeSuggestion.objects.get(pk=pk)
        except AlternativeSuggestion.DoesNotExist:
            return Response({'error': 'الاقتراح غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AlternativeSuggestionReviewSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(reviewed_by=request.user)
            return Response(AlternativeSuggestionSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
