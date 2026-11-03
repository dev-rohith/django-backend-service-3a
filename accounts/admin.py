from django.contrib import admin

from accounts.models import UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "expires_at", "is_active"]
    list_filter = ["created_at"]
    search_fields = ["user__username"]
    readonly_fields = ["token", "created_at"]
