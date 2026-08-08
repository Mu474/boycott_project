from django.urls import path
from .views import SuggestionListView, SuggestionDetailView

urlpatterns = [
    path('', SuggestionListView.as_view(), name='suggestion-list'),
    path('<int:pk>/', SuggestionDetailView.as_view(), name='suggestion-detail'),
]