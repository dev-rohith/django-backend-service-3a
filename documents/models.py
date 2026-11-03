from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from documents.constants import ALLOWED_DOCUMENT_EXTENSIONS
from documents.validators import validate_file_size


class Document(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        blank=True,
        validators=[
            FileExtensionValidator(ALLOWED_DOCUMENT_EXTENSIONS),
            validate_file_size,
        ],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class QueryLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="query_logs"
    )
    query_text = models.CharField(max_length=500)
    result_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.query_text[:40]}"


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index"]
        unique_together = [["document", "chunk_index"]]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document}"
