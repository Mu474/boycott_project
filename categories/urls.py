from django.urls import path
from .views import CategoryListView, CategoryDetailView, SubcategoryListView

urlpatterns = [
    path('', CategoryListView.as_view(), name='category-list'),
    path('<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('<int:pk>/subcategories/', SubcategoryListView.as_view(), name='subcategory-list'),
]