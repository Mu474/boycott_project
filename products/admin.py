from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'barcode', 'status', 'category', 'entity', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['name', 'barcode']