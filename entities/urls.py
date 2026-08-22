from django.urls import path
from .views import (
    EntityListView, EntityDetailView,
    EntitySubsidiariesView, EntityProductsView,
    EntityAlternativesView, EntityTopBoycottedView,
    EntityRandomAlternativesView,
    EntityTreeView, EntityAncestorsView
)

urlpatterns = [
    path('', EntityListView.as_view(), name='entity-list'),
    path('top-boycotted/', EntityTopBoycottedView.as_view(), name='entity-top-boycotted'),
    path('alternatives/random/', EntityRandomAlternativesView.as_view(), name='entity-random-alternatives'),
    path('<int:pk>/', EntityDetailView.as_view(), name='entity-detail'),
    path('<int:pk>/subsidiaries/', EntitySubsidiariesView.as_view(), name='entity-subsidiaries'),
    path('<int:pk>/products/', EntityProductsView.as_view(), name='entity-products'),
    path('<int:pk>/alternatives/', EntityAlternativesView.as_view(), name='entity-alternatives'),
    path('<int:pk>/tree/', EntityTreeView.as_view(), name='entity-tree'),
    path('<int:pk>/ancestors/', EntityAncestorsView.as_view(), name='entity-ancestors'),
]