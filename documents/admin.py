from django.contrib import admin

from documents.models import Document, DocumentChunk, QueryLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "uploaded_at"]
    list_filter = ["uploaded_at"]
    search_fields = ["title"]


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ["user", "query_text", "result_summary", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["query_text"]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["chunk_text"]
