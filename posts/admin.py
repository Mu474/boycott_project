from django.contrib import admin
from .models import CommunityPost, PostReaction, AlternativeSuggestion


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post_type', 'title', 'status', 'created_at']
    list_filter = ['post_type', 'status']
    search_fields = ['title', 'body', 'user__email', 'user__username']
    readonly_fields = ['created_at', 'published_at']


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post', 'created_at']


@admin.register(AlternativeSuggestion)
class AlternativeSuggestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'source_product', 'suggested_product', 'status', 'created_at']
    list_filter = ['status']
