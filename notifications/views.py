from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)[:50]
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class UnreadCountView(APIView):
    """
    endpoint خفيف مخصّص للـ badge — رقم بس بدون أي بيانات ثانية، عشان
    نقدر نستدعيه بشكل متكرر (كل ما تُفتح الشاشة الرئيسية مثلًا) بدون
    تكلفة شبكة/معالجة ملموسة.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        updated = Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
        if not updated:
            return Response({'error': 'الإشعار غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True})


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': True})
