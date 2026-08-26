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
            'data_json', 'image', 'status', 'rejection_reason', 'user', 'reviewed_by', 'created_at'
        ]
        read_only_fields = ['status', 'rejection_reason', 'reviewed_by', 'created_at']


class SuggestionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        # أضفنا target_id هنا — قبل كذا ما كان مسموح تحديثه، فلما نوافق على
        # اقتراح وننشئ منتج/جهة فعليًا، ما كان فيه طريقة نربط الاقتراح
        # بالعنصر الجديد اللي انولد منه.
        # rejection_reason جديد — يسمح للأدمن يكتب سبب الرفض وقت الرفض نفسه
        fields = ['status', 'reviewed_by', 'target_id', 'rejection_reason']
