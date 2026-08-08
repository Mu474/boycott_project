from django.contrib import admin
from .models import BusinessEntity

@admin.register(BusinessEntity)
class BusinessEntityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'category', 'parent_entity', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['name']