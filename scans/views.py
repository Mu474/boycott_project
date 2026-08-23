from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import ScanHistory
from .serializers import ScanHistorySerializer


class ScanHistorySyncView(APIView):
    """
    مزامنة دفعية (bulk) لسجلات مسح محلية غير مُزامَنة — التطبيق يستدعيها
    لما يرجع أونلاين بعد فترة أوفلاين (أو بعد كل مسح مباشرة لو متصل).

    Idempotent عن قصد: إعادة إرسال نفس client_uuid (بسبب إعادة محاولة
    تلقائية من التطبيق مثلًا) ما تُنشئ نسخة مكرّرة — نتجاهلها بصمت.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response(
                {'error': 'صيغة الطلب غير صحيحة — متوقّع قائمة سجلات (أو {"items": [...]})'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_uuids = []
        skipped_uuids = []  # موجودة أصلًا (مزامنة سابقة ناجحة) — مو خطأ
        errors = []

        for item in items:
            client_uuid = item.get('client_uuid')
            if not client_uuid:
                errors.append({'item': item, 'error': 'client_uuid مطلوب'})
                continue

            if ScanHistory.objects.filter(client_uuid=client_uuid).exists():
                skipped_uuids.append(client_uuid)
                continue

            serializer = ScanHistorySerializer(data=item)
            if not serializer.is_valid():
                errors.append({'client_uuid': client_uuid, 'error': serializer.errors})
                continue

            try:
                serializer.save(user=request.user)
                created_uuids.append(client_uuid)
            except IntegrityError:
                # سباق نادر: طلب مزامنة آخر (متزامن بنفس اللحظة) أنشأها
                # أول بمايكرو-ثانية — نعتبرها كأنها موجودة أصلًا، مو خطأ
                skipped_uuids.append(client_uuid)

        return Response(
            {'created': created_uuids, 'skipped': skipped_uuids, 'errors': errors},
            status=status.HTTP_200_OK,
        )


class ScanHistoryListView(APIView):
    """سجل مسح المستخدم نفسه من السيرفر — أحدث 200 سجلّة."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scans = ScanHistory.objects.filter(user=request.user).order_by('-scanned_at')[:200]
        serializer = ScanHistorySerializer(scans, many=True)
        return Response(serializer.data)
