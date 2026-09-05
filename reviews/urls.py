from django.urls import path
from .views import (
    ProductReviewListView, EntityReviewListView,
    ReviewCreateView, ReviewUpdateDeleteView,
)

urlpatterns = [
    path('product/<int:product_id>/', ProductReviewListView.as_view(), name='review-by-product'),
    path('entity/<int:entity_id>/', EntityReviewListView.as_view(), name='review-by-entity'),
    path('<int:pk>/', ReviewUpdateDeleteView.as_view(), name='review-update-delete'),
    path('', ReviewCreateView.as_view(), name='review-create'),
]
