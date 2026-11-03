import logging
import uuid

import pypdf
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.services.chunker import split
from ai.services.vector_store import store
from documents.models import Document, DocumentChunk

from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from .services.agent import agent

logger = logging.getLogger(__name__)


def _extract_text(file) -> str:
    if file.name.lower().endswith(".pdf"):
        reader = pypdf.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file.read().decode("utf-8", errors="replace")


class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        if not (file.name.lower().endswith(".pdf") or file.name.lower().endswith(".txt")):
            return Response(
                {"error": "Only PDF and TXT files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = _extract_text(file)
        if not text.strip():
            return Response(
                {"error": "Could not extract text from the file."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        with transaction.atomic():
            doc = Document.objects.create(owner=request.user, title=file.name, content=text)
            chunks = DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(document=doc, chunk_index=i, chunk_text=t)
                    for i, t in enumerate(split(text))
                ]
            )

        for chunk in chunks:
            store.add(chunk.id, str(doc.id), chunk.chunk_text)

        logger.info(
            "file %s ingested: %d chunks by user %s", file.name, len(chunks), request.user.pk
        )
        return Response(
            {"status": "success", "document_id": doc.id, "chunk_count": len(chunks)},
            status=status.HTTP_201_CREATED,
        )


class ChatView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"]
        session_key = serializer.validated_data.get("session_id") or uuid.uuid4()

        session, _ = ChatSession.objects.get_or_create(
            user=request.user,
            session_key=session_key,
        )
        history = list(session.messages.values("role", "content").order_by("created_at"))

        result = agent.invoke({
            "messages": history,
            "query": message,
            "intent": "",
            "context": "",
            "sources": [],
            "response": "",
        })

        response_text = result["response"]
        sources = result["sources"]

        with transaction.atomic():
            ChatMessage.objects.create(session=session, role="user", content=message)
            ChatMessage.objects.create(
                session=session, role="assistant", content=response_text, sources=sources
            )

        logger.info("chat session %s: user %s", session_key, request.user.pk)
        return Response({
            "session_id": str(session.session_key),
            "response": response_text,
            "sources": sources,
        })


class ChatHistoryView(APIView):
    def get(self, request, session_key):
        try:
            session = ChatSession.objects.get(user=request.user, session_key=session_key)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = session.messages.order_by("created_at")[:100]
        return Response({
            "session_key": str(session.session_key),
            "created_at": session.created_at,
            "messages": ChatMessageSerializer(messages, many=True).data,
        })
