import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.constants import MAX_UPLOAD_SIZE_MB
from documents.models import Document, QueryLog
from documents.permissions import IsOwner
from documents.serializers import (
    DocumentListSerializer,
    DocumentSerializer,
    QueryLogSerializer,
    QueryRequestSerializer,
)

logger = logging.getLogger(__name__)


def extract_text(uploaded_file):
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    return raw.decode("utf-8", errors="ignore")


class DocumentListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return DocumentListSerializer if self.request.method == "GET" else DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).select_related("owner")

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if uploaded_file and uploaded_file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return Response(
                {"error": f"File exceeds the {MAX_UPLOAD_SIZE_MB}MB limit."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        uploaded_file = serializer.validated_data.get("file")
        content = serializer.validated_data.get("content", "")
        if uploaded_file and not content:
            content = extract_text(uploaded_file)
        doc = serializer.save(owner=self.request.user, content=content)
        logger.info("document %s created by user %s", doc.pk, self.request.user.pk)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.method == "DELETE":
            return Document.objects.all().select_related("owner")
        return Document.objects.filter(owner=self.request.user).select_related("owner")

    def perform_destroy(self, instance):
        stored_file = instance.file
        instance.delete()
        if stored_file:
            transaction.on_commit(lambda: stored_file.delete(save=False))
        logger.info("document %s deleted by user %s", instance.pk, self.request.user.pk)


class RunQueryView(APIView):
    def post(self, request):
        serializer = QueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query_text = serializer.validated_data["query_text"]

        count = (
            Document.objects.filter(owner=request.user)
            .filter(Q(title__icontains=query_text) | Q(content__icontains=query_text))
            .count()
        )
        summary = f"Found {count} document{'s' if count != 1 else ''} matching '{query_text}'."

        log = QueryLog.objects.create(
            user=request.user,
            query_text=query_text,
            result_summary=summary,
        )
        return Response(QueryLogSerializer(log).data, status=status.HTTP_201_CREATED)


class QueryLogListView(generics.ListAPIView):
    serializer_class = QueryLogSerializer

    def get_queryset(self):
        return QueryLog.objects.filter(user=self.request.user)
