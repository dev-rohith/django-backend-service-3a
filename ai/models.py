from django.conf import settings
from django.db import models


class AIQueryHistory(models.Model):
    QUERY_TYPES = [
        ("ask_ai", "Ask AI"),
        ("rag_query", "RAG Query"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_query_history",
    )
    query_type = models.CharField(max_length=20, choices=QUERY_TYPES)
    prompt = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.query_type} @ {self.created_at:%Y-%m-%d %H:%M}"
