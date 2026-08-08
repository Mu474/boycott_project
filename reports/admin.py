from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'target_type', 'target_id', 'status', 'user', 'created_at']
    list_filter = ['status', 'target_type']