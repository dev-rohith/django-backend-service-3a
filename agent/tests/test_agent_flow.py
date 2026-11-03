from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from agent.models import ChatMessage


@pytest.fixture
def agent_client(db):
    user = User.objects.create_user(username="testuser", password="testpass123")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, user


@pytest.mark.django_db
class TestAgentEndToEnd:
    def test_rag_agent_flow(self, agent_client):
        """Upload intent: agent routes to RAG, returns answer with source chunks."""
        client, _ = agent_client
        mock_sources = [{"document_id": "1", "chunk_text": "Python is a programming language."}]

        with (
            patch("agent.services.agent._llm") as mock_llm_factory,
            patch("agent.services.tools.store") as mock_store,
        ):
            mock_store.search.return_value = mock_sources

            llm = MagicMock()
            llm.invoke.side_effect = [
                MagicMock(content="rag"),
                MagicMock(content="Python is a high-level programming language."),
            ]
            mock_llm_factory.return_value = llm

            r = client.post(
                "/api/agent/chat/",
                {"message": "What is Python?"},
                format="json",
            )

        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "session_id" in data
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

    def test_weather_agent_flow(self, agent_client):
        """Weather intent: agent routes to weather tool and returns temperature data."""
        client, _ = agent_client

        with (
            patch("agent.services.agent._llm") as mock_llm_factory,
            patch("agent.services.tools.requests.get") as mock_get,
        ):
            geo_resp = MagicMock()
            geo_resp.json.return_value = {
                "results": [{"latitude": 51.5, "longitude": -0.1}]
            }
            weather_resp = MagicMock()
            weather_resp.json.return_value = {
                "current_weather": {"temperature": 15.2, "windspeed": 12.0, "weathercode": 1}
            }
            mock_get.side_effect = [geo_resp, weather_resp]

            llm = MagicMock()
            llm.invoke.side_effect = [
                MagicMock(content="weather"),
                MagicMock(content="London"),
                MagicMock(content="It is currently 15.2°C in London."),
            ]
            mock_llm_factory.return_value = llm

            r = client.post(
                "/api/agent/chat/",
                {"message": "What is the weather in London?"},
                format="json",
            )

        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert data["sources"] == []

    def test_session_memory_persists(self, agent_client):
        """Messages from the same session_id are stored and passed as history."""
        client, _ = agent_client
        session_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

        with patch("agent.services.agent._llm") as mock_llm_factory:
            llm = MagicMock()
            llm.invoke.side_effect = [
                MagicMock(content="general"),
                MagicMock(content="I am a helpful AI assistant."),
                MagicMock(content="general"),
                MagicMock(content="You asked what I am."),
            ]
            mock_llm_factory.return_value = llm

            r1 = client.post(
                "/api/agent/chat/",
                {"message": "What are you?", "session_id": session_id},
                format="json",
            )
            r2 = client.post(
                "/api/agent/chat/",
                {"message": "What did I just ask?", "session_id": session_id},
                format="json",
            )

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["session_id"] == r2.json()["session_id"]

        msgs = ChatMessage.objects.filter(session__session_key=session_id).order_by("created_at")
        assert msgs.count() == 4
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"

    def test_general_intent_no_sources(self, agent_client):
        """General questions return a response with an empty sources list."""
        client, _ = agent_client

        with patch("agent.services.agent._llm") as mock_llm_factory:
            llm = MagicMock()
            llm.invoke.side_effect = [
                MagicMock(content="general"),
                MagicMock(content="The capital of France is Paris."),
            ]
            mock_llm_factory.return_value = llm

            r = client.post(
                "/api/agent/chat/",
                {"message": "What is the capital of France?"},
                format="json",
            )

        assert r.status_code == 200
        assert r.json()["sources"] == []
        assert "response" in r.json()
