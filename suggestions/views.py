import json
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
        # multipart/form-data (لما فيه صورة مرفقة) ما يقدر يرسل JSON
        # متداخل مباشرة — التطبيق يرسل data_json كنص JSON-encoded بهذي
        # الحالة. طلب JSON عادي (بدون صورة) يوصل أصلًا كقاموس جاهز.
        #
        # مهم جدًا (اكتُشف بالاختبار الفعلي، مو افتراضًا): request.data
        # لمولتيبارت هو QueryDict، وحقل JSONField بمكتبة DRF يتعامل مع
        # أي QueryDict كـ"HTML form input" ويلف القيمة تلقائيًا بصنف
        # JSONString عبر repr() بايثون (علامات اقتباس مفردة) — حتى لو
        # كنا فعليًا حوّلناها لـ dict بأنفسنا مسبقًا! هذا يكسرها كـJSON
        # صالح دائمًا. الحل الوحيد الصحيح: نحوّل QueryDict كامل لقاموس
        # عادي (plain dict) قبل أي شيء، مو نستخدم .copy() اللي يبقيها
        # QueryDict بنفس السلوك الإشكالي.
        raw_data = request.data
        if hasattr(raw_data, 'getlist'):
            # QueryDict (multipart) — نبني قاموس عادي يدويًا، قيمة وحيدة
            # لكل مفتاح. لاحظ: dict(raw_data) هنا خطأ خفي — QueryDict هو
            # subclass مباشر من dict نفسه (يمر شرط isinstance(x, dict))،
            # فـ dict(raw_data) يكشف التخزين الداخلي الخام لـ
            # MultiValueDict (كل قيمة كـ list حتى لو عنصر وحيد: {'type':
            # ['add']}) بدل القيمة المفردة المتوقعة — لازم .keys() +
            # __getitem__ صراحة لكل مفتاح لتفادي هذا.
            data = {key: raw_data[key] for key in raw_data.keys()}
        else:
            data = dict(raw_data)

        raw_data_json = data.get('data_json')
        if isinstance(raw_data_json, str):
            try:
                data['data_json'] = json.loads(raw_data_json)
            except (TypeError, ValueError):
                return Response({'data_json': 'صيغة JSON غير صحيحة'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SuggestionSerializer(data=data)
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
