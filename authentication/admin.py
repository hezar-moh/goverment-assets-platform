# Purpose: Register CustomUser with Django admin so Super Admin can manage users.

from django.contrib import admin
from django.utils.html import format_html
from .models import CustomUser


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'email', 'role', 'ministry_schema',
        'is_active', 'lock_status', 'date_joined',
    )
    list_filter = ('is_locked', 'is_active', 'role', 'ministry_schema')
    search_fields = ('username', 'email',)
    ordering = ('-date_joined',)

    def lock_status(self, obj):
        if obj.is_locked:
            return format_html(
                '<span style="background:#fef2f2;color:#dc2626;'
                'padding:2px 10px;border-radius:100px;font-size:11px;'
                'font-weight:600;">Locked</span>'
            )
        return format_html(
            '<span style="background:#f0fdf4;color:#16a34a;'
            'padding:2px 10px;border-radius:100px;font-size:11px;'
            'font-weight:600;">Active</span>'
        )
    lock_status.short_description = 'Lock Status'

    actions = ['unlock_selected']

    def unlock_selected(self, request, queryset):
        from django.contrib import messages
        updated = queryset.update(is_locked=False)
        self.message_user(
            request,
            f'{updated} user(s) unlocked successfully.',
            messages.SUCCESS,
        )
    unlock_selected.short_description = 'Unlock selected users'


admin.site.register(CustomUser, CustomUserAdmin)