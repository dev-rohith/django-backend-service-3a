import pytest
from rest_framework import status

from documents.models import Document, QueryLog

pytestmark = pytest.mark.django_db


def make_document(owner, title, text):
    return Document.objects.create(owner=owner, title=title, content=text)


def test_query_creates_and_returns_query_log(auth_client, user):
    make_document(user, "Recipe", "how to bake sourdough bread")

    response = auth_client.post("/api/query", {"query_text": "bake"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["query_text"] == "bake"
    assert "result_summary" in response.data
    assert "id" in response.data
    assert "created_at" in response.data


def test_query_summary_reflects_match_count(auth_client, user):
    make_document(user, "Recipe", "how to bake sourdough bread")
    make_document(user, "Manual", "how to fix a bicycle chain")

    response = auth_client.post("/api/query", {"query_text": "bake"})

    assert response.status_code == status.HTTP_201_CREATED
    assert "1" in response.data["result_summary"]


def test_query_only_searches_own_documents(auth_client, user, other_user):
    make_document(other_user, "Secret", "the launch code is bake1234")

    response = auth_client.post("/api/query", {"query_text": "bake"})

    assert response.status_code == status.HTTP_201_CREATED
    assert "0" in response.data["result_summary"]


def test_query_creates_a_log_entry(auth_client, user):
    make_document(user, "Recipe", "how to bake sourdough bread")

    auth_client.post("/api/query", {"query_text": "bake"})

    log_entry = QueryLog.objects.get(user=user)
    assert log_entry.query_text == "bake"
    assert log_entry.result_summary != ""


def test_query_history_is_paginated_and_scoped(auth_client, user, other_user):
    QueryLog.objects.create(user=other_user, query_text="not mine", result_summary="")
    for index in range(12):
        QueryLog.objects.create(user=user, query_text=f"search {index}", result_summary="")

    response = auth_client.get("/api/queries")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 10


def test_query_rejects_blank_query_text(auth_client, user):
    response = auth_client.post("/api/query", {"query_text": ""})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not QueryLog.objects.exists()


def test_query_requires_authentication(api_client):
    response = api_client.post("/api/query", {"query_text": "bake"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_queries_endpoint_requires_authentication(api_client):
    response = api_client.get("/api/queries")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_query_history_page_size_override(auth_client, user):
    for index in range(6):
        QueryLog.objects.create(user=user, query_text=f"q{index}", result_summary="")

    response = auth_client.get("/api/queries", {"page_size": 3})

    assert len(response.data["results"]) == 3
    assert response.data["count"] == 6
