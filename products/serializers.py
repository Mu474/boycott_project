from rest_framework import serializers
from .models import Product
from entities.serializers import EntityMinimalSerializer
from categories.serializers import CategorySerializer


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'barcode',
            'status', 'reason', 'evidence_url',
            'category', 'entity', 'created_at'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    entity = EntityMinimalSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'image', 'barcode',
            'status', 'reason', 'evidence_url',
            'category', 'entity', 'created_at'
        ]