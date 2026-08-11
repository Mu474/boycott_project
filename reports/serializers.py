from rest_framework import serializers
from .models import Report
from users.models import User


class ReportUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class ReportSerializer(serializers.ModelSerializer):
    user = ReportUserSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'category', 'target_type', 'target_id', 'target_name',
            'reason', 'status', 'user', 'reviewed_by', 'created_at'
        ]
        read_only_fields = ['status', 'reviewed_by', 'created_at']


class ReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['status', 'reviewed_by']
