from rest_framework import serializers
from .models import Suggestion
from users.models import User


class SuggestionUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class SuggestionSerializer(serializers.ModelSerializer):
    user = SuggestionUserSerializer(read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            'id', 'type', 'target_type', 'target_id',
            'data_json', 'status', 'user', 'reviewed_by', 'created_at'
        ]
        read_only_fields = ['status', 'reviewed_by', 'created_at']


class SuggestionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        fields = ['status', 'reviewed_by']