from django.contrib import admin
from .models import ScanHistory


@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'barcode', 'product_name_snapshot', 'status_at_scan', 'found', 'scanned_at']
    list_filter = ['found', 'status_at_scan']
    search_fields = ['barcode', 'product_name_snapshot', 'user__email', 'user__name']
    readonly_fields = ['synced_at']
