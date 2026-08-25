from django.db import IntegrityError
from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from products.models import Product
from .models import ScanHistory
from .serializers import ScanHistorySerializer


class ScanHistorySyncView(APIView):
    """
    مزامنة دفعية (bulk) لسجلات مسح محلية غير مُزامَنة — التطبيق يستدعيها
    لما يرجع أونلاين بعد فترة أوفلاين (أو بعد كل مسح مباشرة لو متصل).

    Idempotent عن قصد: إعادة إرسال نفس client_uuid (بسبب إعادة محاولة
    تلقائية من التطبيق مثلًا) ما تُنشئ نسخة مكرّرة — نتجاهلها بصمت.

    مهم جدًا (أمان/مكافحة تلاعب): بما إن سجل المسح صار الآن مصدر نقاط
    (راجع community/points.py)، ما نثق إطلاقًا بحقول product/found/
    product_name_snapshot/status_at_scan اللي يرسلها العميل — أي حد
    يقدر يستدعي هذا الـ endpoint مباشرة (بدون التطبيق نفسه، عبر أي
    أداة) ويحقن أي product id يبيه لاختراع "منتجات ممسوحة" وهمية
    ويكسب نقاط بدون ما يمسح شيء فعليًا. الحل: نتجاهل هذي الحقول تمامًا
    من العميل، ونبحث عن المنتج بالـ barcode بأنفسنا من قاعدتنا، ونحدد
    found/product/الحالة من نتيجة هذا البحث فقط — العميل يتحكم بالباركود
    فقط، مو بنتيجة المطابقة.
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
            barcode = (item.get('barcode') or '').strip()

            if not client_uuid:
                errors.append({'item': item, 'error': 'client_uuid مطلوب'})
                continue
            if not barcode:
                errors.append({'client_uuid': client_uuid, 'error': 'barcode مطلوب'})
                continue

            if ScanHistory.objects.filter(client_uuid=client_uuid).exists():
                skipped_uuids.append(client_uuid)
                continue

            # البحث الموثوق (سيرفري) عن المنتج — العميل ما يقدر يزوّر هذا
            product = Product.objects.filter(barcode=barcode).first()

            serializer = ScanHistorySerializer(data={
                'client_uuid': client_uuid,
                'barcode': barcode,
                'scanned_at': item.get('scanned_at'),
                'found': product is not None,
                'product': product.id if product else None,
                'product_name_snapshot': product.name if product else '',
                'status_at_scan': product.status if product else '',
            })
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


class ScanStatsView(APIView):
    """
    إحصائيات إدارية مجمّعة عن كل المسح بالنظام (مو مستخدم واحد) —
    endpoint خاص بلوحة التحكم، مو التطبيق. يُستخدم لعرض "أكثر
    المنتجات مسحًا" بالداشبورد.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        top_products = (
            ScanHistory.objects.filter(product__isnull=False)
            .values('product_id', 'product__name')
            .annotate(scan_count=Count('id'))
            .order_by('-scan_count')[:10]
        )
        return Response({
            'total_scans': ScanHistory.objects.count(),
            'not_found_scans': ScanHistory.objects.filter(found=False).count(),
            'top_products': [
                {'product_id': p['product_id'], 'name': p['product__name'], 'count': p['scan_count']}
                for p in top_products
            ],
        })
