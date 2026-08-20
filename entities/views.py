from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import ProtectedError
from django.db import models as db_models
from .models import BusinessEntity
from .serializers import EntitySerializer, EntityDetailSerializer, EntityMinimalSerializer
from products.serializers import ProductSerializer
from .filters import EntityFilter


def cascade_status(entity_id, new_status):
    from entities.models import BusinessEntity
    from products.models import Product
    children = BusinessEntity.objects.filter(parent_entity_id=entity_id)
    children.update(status=new_status)
    for child in children:
        cascade_status(child.id, new_status)
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