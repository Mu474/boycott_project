from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'username', 'is_staff', 'is_superuser', 'created_at']


class MeSerializer(serializers.ModelSerializer):
    """
    الملف الشخصي للمستخدم الحالي — يشمل النقاط (محسوبة ديناميكيًا،
    راجع community/points.py لتفاصيل ليش مو حقل مخزَّن).
    """
    points = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'username', 'is_staff', 'points', 'created_at']

    def get_points(self, obj):
        from community.points import calculate_points
        return calculate_points(obj)
