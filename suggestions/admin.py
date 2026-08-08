from django.contrib import admin
from .models import Suggestion

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'target_type', 'status', 'user', 'created_at']
    list_filter = ['status', 'type', 'target_type']