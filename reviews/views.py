from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Review
from .serializers import ReviewSerializer


class ProductReviewListView(APIView):
    """كل تقييمات منتج معيّن — عام، أي زائر يشوفها."""
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id, status='visible')
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)


class EntityReviewListView(APIView):
    """كل تقييمات جهة تجارية معيّنة — عام."""
    permission_classes = [AllowAny]

    def get(self, request, entity_id):
        reviews = Review.objects.filter(entity_id=entity_id, status='visible')
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)


class ReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewUpdateDeleteView(APIView):
    """تعديل/حذف تقييمك أنت فقط — لا يوجد مسار أدمن منفصل هنا عمدًا،
    الإبلاغ عن تقييم مخالف يمر عبر Report العام (target_type='review')
    بنفس آلية الإخفاء التلقائي المستخدمة لمنشورات المجتمع."""
    permission_classes = [IsAuthenticated]

    def _get_owned(self, request, pk):
        try:
            return Review.objects.get(pk=pk, user=request.user)
        except Review.DoesNotExist:
            return None

    def patch(self, request, pk):
        review = self._get_owned(request, pk)
        if review is None:
            return Response({'error': 'التقييم غير موجود أو ليس ملكك'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReviewSerializer(review, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        review = self._get_owned(request, pk)
        if review is None:
            return Response({'error': 'التقييم غير موجود أو ليس ملكك'}, status=status.HTTP_404_NOT_FOUND)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
