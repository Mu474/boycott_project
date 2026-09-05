from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'entity', 'rating', 'status', 'created_at']
    list_filter = ['rating', 'status']
    search_fields = ['body', 'user__email', 'user__username', 'product__name', 'entity__name']
