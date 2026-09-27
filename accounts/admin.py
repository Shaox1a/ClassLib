from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ClassLibUserAdmin(UserAdmin):
    list_display = ('username', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (('ClassLib', {'fields': ('role', 'created_at')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('ClassLib', {'fields': ('role',)}),)
    readonly_fields = UserAdmin.readonly_fields + ('created_at',)
