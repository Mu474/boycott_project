from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import ProtectedError, Count
from django.db import models as db_models
from .models import BusinessEntity
from .serializers import EntitySerializer, EntityDetailSerializer, EntityMinimalSerializer
from products.serializers import ProductSerializer
from .filters import EntityFilter


def cascade_status(entity_id, new_status, visited=None):
    from entities.models import BusinessEntity
    from products.models import Product

    # حماية دفاعية: لو وُجدت حلقة دائرية بالبيانات (رغم منعها الآن عند
    # الحفظ بـ EntitySerializer.validate)، نوقف الانتشار هنا بدل ما ندخل
    # بـ recursion لا نهائي يكرش السيرفر
    if visited is None:
        visited = set()
    if entity_id in visited:
        return
    visited.add(entity_id)

    children = BusinessEntity.objects.filter(parent_entity_id=entity_id)
    children.update(status=new_status)
    for child in children:
        cascade_status(child.id, new_status, visited)
    Product.objects.filter(entity_id=entity_id).update(status=new_status)


class EntityListView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        # select_related يحوّل الاستعلامات المنفصلة لكل تصنيف/جهة أم
        # (N+1 queries — مشكلة أداء حقيقية على قاعدة بيانات بعيدة زي
        # Supabase) لاستعلام SQL واحد فيه JOIN. بدونه، صفحة فيها 900+
        # جهة كانت تسوي ~1800 استعلام منفصل بدل استعلام واحد.
        entities = BusinessEntity.objects.select_related('category', 'parent_entity').all()
        filtered = EntityFilter(request.GET, queryset=entities).qs
        serializer = EntityDetailSerializer(filtered, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = EntitySerializer(data=request.data)
        if serializer.is_valid():
            entity = serializer.save()
            return Response(EntityDetailSerializer(entity, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EntityDetailView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get_object(self, pk):
        try:
            return BusinessEntity.objects.get(pk=pk)
        except BusinessEntity.DoesNotExist:
            return None

    def get(self, request, pk):
        entity = self.get_object(pk)
        if not entity:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EntityDetailSerializer(entity, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        entity = self.get_object(pk)
        if not entity:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        old_status = entity.status
        serializer = EntitySerializer(entity, data=request.data)
        if serializer.is_valid():
            entity = serializer.save()
            if entity.status != old_status:
                cascade_status(entity.id, entity.status)
            return Response(EntityDetailSerializer(entity, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        entity = self.get_object(pk)
        if not entity:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        try:
            entity.delete()
        except ProtectedError:
            return Response(
                {'error': 'لا يمكن حذف هذه الجهة لأنها مرتبطة بمنتجات مسجّلة. عدّل أو احذف المنتجات المرتبطة بها أولاً.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EntitySubsidiariesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            entity = BusinessEntity.objects.get(pk=pk)
        except BusinessEntity.DoesNotExist:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        subsidiaries = entity.subsidiaries.all()
        serializer = EntityMinimalSerializer(subsidiaries, many=True, context={'request': request})
        return Response(serializer.data)


class EntityProductsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            entity = BusinessEntity.objects.get(pk=pk)
        except BusinessEntity.DoesNotExist:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        products = entity.product_set.all()
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class EntityAlternativesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            entity = BusinessEntity.objects.get(pk=pk)
        except BusinessEntity.DoesNotExist:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)

        # "أخرى" تصنيف عام يجمع مئات الجهات المختلفة تمامًا (بسبب نقص
        # بيانات التصنيف بمصدر الاستيراد الخارجي) — مطابقته حرفيًا
        # تنتج بدائل عشوائية غير منطقية (شركة سيارات كبديل لشركة أزياء
        # مثلاً). لما يكون تصنيف الجهة "أخرى"، نرجع بدائل عامة بدل
        # مطابقة مضلّلة توحي بعلاقة فعلية غير موجودة.
        if entity.category.name == 'أخرى':
            alternatives = BusinessEntity.objects.filter(
                status='alternative'
            ).exclude(pk=pk).order_by('?')[:10]
        else:
            alternatives = BusinessEntity.objects.filter(
                category=entity.category,
                status='alternative'
            ).exclude(pk=pk)
        serializer = EntityMinimalSerializer(alternatives, many=True, context={'request': request})
        return Response(serializer.data)


class EntityTopBoycottedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Count
        entities = BusinessEntity.objects.annotate(
            boycott_count=Count(
                'product',
                filter=db_models.Q(product__status='boycott')
            )
        ).filter(boycott_count__gt=0).order_by('-boycott_count')[:10]
        serializer = EntityMinimalSerializer(entities, many=True, context={'request': request})
        return Response(serializer.data)


class EntityRandomAlternativesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        entities = BusinessEntity.objects.filter(
            status='alternative'
        ).order_by('?')[:10]
        serializer = EntityMinimalSerializer(entities, many=True, context={'request': request})
        return Response(serializer.data)


class EntityTreeView(APIView):
    """
    يرجّع الهيكل التجاري كاملًا لجهة معيّنة (كل أبنائها بكل المستويات
    دفعة وحدة)، بدل ما تضطر الواجهة تسوي استدعاء API منفصل لكل مستوى.

    نحمّل كل الجهات باستعلام SQL واحد ثم نبني الشجرة في بايثون —
    نفس فلسفة select_related الموجودة بـ EntityListView لتفادي N+1،
    لكن هنا حتى أعمق من مستوى واحد.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            pk = int(pk)
        except (TypeError, ValueError):
            return Response({'error': 'معرّف غير صالح'}, status=status.HTTP_400_BAD_REQUEST)

        entities = list(
            BusinessEntity.objects.annotate(product_count=Count('product'))
        )
        entities_by_id = {e.id: e for e in entities}

        if pk not in entities_by_id:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)

        children_map = {}
        for e in entities:
            children_map.setdefault(e.parent_entity_id, []).append(e.id)

        def build(entity_id, visited):
            # حماية دفاعية من حلقة دائرية باقية بالبيانات (خط دفاع ثانٍ
            # بعد التحقق عند الحفظ بـ EntitySerializer.validate) — لو
            # صادفنا جهة زرناها بنفس المسار، نوقف هالفرع بدل ما ندخل
            # بحلقة لا نهائية تكرش الطلب
            if entity_id in visited:
                return None
            visited = visited | {entity_id}

            e = entities_by_id[entity_id]
            children = [
                node for cid in children_map.get(entity_id, [])
                if (node := build(cid, visited)) is not None
            ]
            return {
                'id': e.id,
                'name': e.name,
                'logo': request.build_absolute_uri(e.logo.url) if e.logo else None,
                'status': e.status,
                'product_count': e.product_count,
                'children': children,
            }

        tree = build(pk, frozenset())
        return Response(tree)


class EntityAncestorsView(APIView):
    """
    يرجّع مسار الأجداد من الجذر حتى الأب المباشر لجهة معيّنة (بدون
    الجهة نفسها) — يُستخدم لعرض "الشركة المالكة → العلامة" (breadcrumb)
    لما يدخل المستخدم من جهة تابعة مباشرة، بدل ما يبدأ من الجذر.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            entity = BusinessEntity.objects.select_related('parent_entity').get(pk=pk)
        except BusinessEntity.DoesNotExist:
            return Response({'error': 'الجهة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)

        ancestors = []
        visited = set()
        current = entity.parent_entity
        while current is not None and current.id not in visited:
            visited.add(current.id)
            ancestors.append(current)
            current = current.parent_entity

        ancestors.reverse()  # من الجذر إلى الأب المباشر
        serializer = EntityMinimalSerializer(ancestors, many=True, context={'request': request})
        return Response(serializer.data)