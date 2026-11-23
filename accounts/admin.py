from django.contrib import admin
from .models import User


@admin.register(User)
class ClassLibUserAdmin(admin.ModelAdmin):
    """Inspect accounts here; use ClassLib's forms for guarded mutations."""
    list_display = ('username', 'nickname', 'permission_group', 'is_active', 'created_at')
    list_filter = ('permission_group', 'is_active')
    fields = readonly_fields = ('username', 'nickname', 'permission_group', 'is_active', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
