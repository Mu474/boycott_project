from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Suggestion
from .serializers import SuggestionSerializer, SuggestionUpdateSerializer
from notifications.services import notify_suggestion_reviewed


class SuggestionListView(APIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get(self, request):
        suggestions = Suggestion.objects.all().order_by('-created_at')
        serializer = SuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SuggestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SuggestionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, pk):
        try:
            return Suggestion.objects.get(pk=pk)
        except Suggestion.DoesNotExist:
            return None

    def get(self, request, pk):
        suggestion = self.get_object(pk)
        if not suggestion:
            return Response({'error': 'الاقتراح غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SuggestionSerializer(suggestion)
        return Response(serializer.data)

    def patch(self, request, pk):
        suggestion = self.get_object(pk)
        if not suggestion:
            return Response({'error': 'الاقتراح غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        previous_status = suggestion.status
        serializer = SuggestionUpdateSerializer(suggestion, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # إشعار بس لو الحالة تغيّرت فعليًا لحالة نهائية — لا نكرره لو
            # الأدمن حدّث حقل ثاني (مثلاً target_id) بدون تغيير status نفسها
            if previous_status != suggestion.status and suggestion.status in ('approved', 'rejected'):
                notify_suggestion_reviewed(suggestion)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
