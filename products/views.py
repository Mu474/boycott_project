from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import Q
from .models import Product
from .serializers import ProductSerializer, ProductDetailSerializer


class ProductListView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        # نفس إصلاح الجهات — يمنع استعلام منفصل لكل تصنيف/جهة لكل منتج
        products = Product.objects.select_related('category', 'entity').all()

        status_filter = request.query_params.get('status')
        if status_filter in ['boycott', 'caution', 'alternative']:
            products = products.filter(status=status_filter)

        category_filter = request.query_params.get('category')
        if category_filter:
            products = products.filter(category__id=category_filter)

        search = request.query_params.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(barcode__icontains=search)
            )

        serializer = ProductDetailSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(ProductDetailSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    def get_object(self, pk):
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return None

    def get(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(ProductDetailSerializer(product, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = self.get_object(pk)
        if not product:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductBarcodeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        try:
            product = Product.objects.get(barcode=code)
        except Product.DoesNotExist:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data)


class ProductSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'أدخل كلمة للبحث'}, status=status.HTTP_400_BAD_REQUEST)
        products = Product.objects.filter(name__icontains=query)
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductAlternativesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'المنتج غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        alternatives = Product.objects.filter(
            category=product.category,
            status='alternative'
        ).exclude(pk=pk)
        serializer = ProductSerializer(alternatives, many=True, context={'request': request})
        return Response(serializer.data)


class ProductRandomAlternativesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.filter(
            status='alternative'
        ).order_by('?')[:10]
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)