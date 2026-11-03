import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document, DocumentChunk

from .constants import TOP_K
from .models import AIQueryHistory
from .serializers import (
    AIQueryHistorySerializer,
    AskAIRequestSerializer,
    IngestDocRequestSerializer,
    RAGQueryRequestSerializer,
)
from .services.chunker import split
from .services.llm_service import ask, rag_answer
from .services.vector_store import store

logger = logging.getLogger(__name__)


class AskAIView(APIView):
    def post(self, request):
        serializer = AskAIRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data["prompt"]

        response_text = ask(prompt)
        AIQueryHistory.objects.create(
            user=request.user,
            query_type="ask_ai",
            prompt=prompt,
            response=response_text,
        )
        logger.info("ask-ai query by user %s", request.user.pk)
        return Response({"response": response_text})


class IngestDocView(APIView):
    def post(self, request):
        serializer = IngestDocRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_id = serializer.validated_data["document_id"]

        doc = get_object_or_404(Document, pk=doc_id)

        if not doc.content.strip():
            logger.warning("ingest-doc: document %s has no text content", doc_id)
            return Response(
                {"error": "Document has no extractable text content."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        old_ids = list(doc.chunks.values_list("id", flat=True))

        with transaction.atomic():
            doc.chunks.all().delete()
            chunks = DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(document=doc, chunk_index=i, chunk_text=t)
                    for i, t in enumerate(split(doc.content))
                ]
            )

        store.remove(old_ids)
        for chunk in chunks:
            store.add(chunk.id, str(doc_id), chunk.chunk_text)

        logger.info(
            "document %s ingested into %d chunks by user %s", doc_id, len(chunks), request.user.pk
        )
        return Response({"status": "success", "chunk_count": len(chunks)})


class RAGQueryView(APIView):
    def post(self, request):
        serializer = RAGQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]

        results = store.search(query, k=TOP_K)
        if not results:
            return Response(
                {"error": "No ingested documents found. Use POST /api/ingest-doc first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        answer = rag_answer(query, [r["chunk_text"] for r in results])
        AIQueryHistory.objects.create(
            user=request.user,
            query_type="rag_query",
            prompt=query,
            response=answer,
        )
        logger.info("rag-query by user %s, %d chunks retrieved", request.user.pk, len(results))
        return Response(
            {
                "answer": answer,
                "source_chunks": [
                    {"document_id": r["document_id"], "chunk_text": r["chunk_text"]}
                    for r in results
                ],
            }
        )


class AIQueryHistoryView(generics.ListAPIView):
    serializer_class = AIQueryHistorySerializer

    def get_queryset(self):
        return AIQueryHistory.objects.filter(user=self.request.user)
