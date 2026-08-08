import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    barcode = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Product.STATUS_CHOICES)
    category = django_filters.NumberFilter(field_name='category__id')

    class Meta:
        model = Product
        fields = ['name', 'barcode', 'status', 'category']