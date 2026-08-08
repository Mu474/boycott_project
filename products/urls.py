from django.urls import path
from .views import (
    ProductListView, ProductDetailView,
    ProductBarcodeView, ProductSearchView,
    ProductAlternativesView, ProductRandomAlternativesView
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('search/', ProductSearchView.as_view(), name='product-search'),
    path('barcode/<str:code>/', ProductBarcodeView.as_view(), name='product-barcode'),
    path('alternatives/random/', ProductRandomAlternativesView.as_view(), name='product-random-alternatives'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('<int:pk>/alternatives/', ProductAlternativesView.as_view(), name='product-alternatives'),
]