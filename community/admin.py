from django.contrib import admin
from .models import Group, GroupMembership, PointTransaction


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'invite_code', 'creator', 'created_at']
    search_fields = ['name', 'invite_code']
    readonly_fields = ['invite_code', 'created_at']
    inlines = [GroupMembershipInline]


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'user', 'joined_at']
    search_fields = ['group__name', 'user__email', 'user__username']


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    """للتدقيق فقط — سحب نقاط معاملة مزيّفة يكون بحذفها من هنا مباشرة."""
    list_display = ['id', 'user', 'action', 'points', 'reference_type', 'reference_id', 'created_at']
    list_filter = ['action']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at']
