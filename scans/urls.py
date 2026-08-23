from django.urls import path
from .views import ScanHistorySyncView, ScanHistoryListView

urlpatterns = [
    path('', ScanHistoryListView.as_view(), name='scan-history-list'),
    path('sync/', ScanHistorySyncView.as_view(), name='scan-history-sync'),
]
