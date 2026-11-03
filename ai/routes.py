from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"^api/ask-ai$", views.AskAIView.as_view(), name="ask-ai"),
    re_path(r"^api/ingest-doc$", views.IngestDocView.as_view(), name="ingest-doc"),
    re_path(r"^api/rag-query$", views.RAGQueryView.as_view(), name="rag-query"),
    re_path(r"^api/query-history$", views.AIQueryHistoryView.as_view(), name="ai-query-history"),
]
