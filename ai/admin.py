from django.contrib import admin

from .models import AIQueryHistory


@admin.register(AIQueryHistory)
class AIQueryHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "query_type", "created_at")
    list_filter = ("query_type",)
    readonly_fields = ("user", "query_type", "prompt", "response", "created_at")
