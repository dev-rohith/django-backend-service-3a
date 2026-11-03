from django.contrib import admin

from agent.models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "session_key", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["session", "role", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = ["content"]
