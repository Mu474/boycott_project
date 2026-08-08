import django_filters
from .models import BusinessEntity

class EntityFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=BusinessEntity.STATUS_CHOICES)
    category = django_filters.NumberFilter(field_name='category__id')

    class Meta:
        model = BusinessEntity
        fields = ['search', 'status', 'category']