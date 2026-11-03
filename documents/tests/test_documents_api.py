import os
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from core.constants import MAX_PAGE_SIZE
from documents.constants import MAX_UPLOAD_SIZE_MB
from documents.models import Document
from documents.permissions import IsOwner

pytestmark = pytest.mark.django_db


def make_text_file(name="notes.txt", content=b"hello from a test document"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


def test_upload_document_via_file(auth_client, user):
    response = auth_client.post(
        "/api/documents",
        {"title": "My Notes", "file": make_text_file()},
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    document = Document.objects.get(title="My Notes")
    assert document.owner == user
    assert "hello from a test document" in document.content


def test_upload_document_via_json_body(auth_client, user):
    response = auth_client.post(
        "/api/documents",
        {"title": "JSON Doc", "content": "Some text content here."},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    document = Document.objects.get(title="JSON Doc")
    assert document.content == "Some text content here."
    assert document.owner == user


def test_upload_rejects_missing_both_file_and_content(auth_client):
    response = auth_client.post(
        "/api/documents", {"title": "Empty"}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_rejects_disallowed_extension(auth_client):
    bad_file = SimpleUploadedFile(
        "virus.exe", b"binary junk", content_type="application/octet-stream"
    )

    response = auth_client.post(
        "/api/documents", {"title": "Bad File", "file": bad_file}, format="multipart"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_documents_only_returns_own(auth_client, user, other_user):
    Document.objects.create(owner=user, title="Mine", content="my content")
    Document.objects.create(owner=other_user, title="Not Mine", content="other content")

    response = auth_client.get("/api/documents")

    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert titles == ["Mine"]


def test_list_documents_is_paginated(auth_client, user):
    for index in range(15):
        Document.objects.create(owner=user, title=f"Doc {index}", content="text")

    response = auth_client.get("/api/documents")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 15
    assert len(response.data["results"]) == 10
    assert response.data["next"] is not None


def test_retrieve_document(auth_client, user):
    document = Document.objects.create(owner=user, title="Readable", content="body")

    response = auth_client.get(f"/api/documents/{document.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Readable"
    assert "content" in response.data


def test_cannot_retrieve_someone_elses_document(auth_client, other_user):
    document = Document.objects.create(owner=other_user, title="Private", content="secret")

    response = auth_client.get(f"/api/documents/{document.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_document(auth_client, user):
    document = Document.objects.create(owner=user, title="Deletable", content="gone")

    response = auth_client.delete(f"/api/documents/{document.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Document.objects.filter(id=document.id).exists()


def test_delete_someone_elses_document_returns_403(auth_client, other_user):
    document = Document.objects.create(owner=other_user, title="Not Yours", content="private")

    response = auth_client.delete(f"/api/documents/{document.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_documents_require_authentication():
    client = APIClient()

    response = client.get("/api/documents")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_rejects_file_over_the_size_limit(auth_client):
    oversized = SimpleUploadedFile(
        "big.txt", b"x" * (MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024, content_type="text/plain"
    )

    response = auth_client.post(
        "/api/documents", {"title": "Too Big", "file": oversized}, format="multipart"
    )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_list_includes_content_field(auth_client, user):
    Document.objects.create(owner=user, title="Doc", content="some text")

    response = auth_client.get("/api/documents")

    assert "content" in response.data["results"][0]


def test_detail_includes_content(auth_client, user):
    document = Document.objects.create(owner=user, title="Doc", content="the full body")

    response = auth_client.get(f"/api/documents/{document.id}")

    assert response.data["content"] == "the full body"


def test_list_query_count_does_not_grow_with_result_count(auth_client, user):
    def count_queries_for(document_count):
        Document.objects.all().delete()
        for index in range(document_count):
            Document.objects.create(owner=user, title=f"D{index}", content="text")
        with CaptureQueriesContext(connection) as ctx:
            auth_client.get("/api/documents")
        return len(ctx.captured_queries)

    assert count_queries_for(2) == count_queries_for(10)


def test_delete_removes_the_stored_file(auth_client, user, django_capture_on_commit_callbacks):
    document = Document.objects.create(
        owner=user, file=make_text_file(), title="Deletable", content="text"
    )
    path = document.file.path
    assert os.path.exists(path)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(f"/api/documents/{document.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not os.path.exists(path)


def test_page_size_can_be_overridden(auth_client, user):
    for index in range(6):
        Document.objects.create(owner=user, title=f"D{index}", content="text")

    response = auth_client.get("/api/documents", {"page_size": 2})

    assert len(response.data["results"]) == 2
    assert response.data["count"] == 6


def test_page_size_is_capped(auth_client, user):
    Document.objects.bulk_create(
        Document(owner=user, title=f"D{index}", content="text")
        for index in range(MAX_PAGE_SIZE + 5)
    )

    response = auth_client.get("/api/documents", {"page_size": 500})

    assert len(response.data["results"]) == MAX_PAGE_SIZE


def test_trailing_slash_resolves(auth_client, user):
    Document.objects.create(owner=user, title="Mine", content="text")

    assert auth_client.get("/api/documents/").status_code == status.HTTP_200_OK


def test_is_owner_permission_rejects_a_non_owner(user, other_user):
    request = SimpleNamespace(user=other_user)

    assert IsOwner().has_object_permission(request, None, Document(owner=user)) is False
    owner_request = SimpleNamespace(user=user)
    assert IsOwner().has_object_permission(owner_request, None, Document(owner=user)) is True
