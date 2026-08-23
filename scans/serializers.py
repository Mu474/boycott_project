from rest_framework import serializers
from .models import ScanHistory


class ScanHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanHistory
        fields = [
            'id', 'client_uuid', 'barcode', 'found', 'product',
            'product_name_snapshot', 'status_at_scan', 'scanned_at', 'synced_at',
        ]
        read_only_fields = ['id', 'synced_at']
