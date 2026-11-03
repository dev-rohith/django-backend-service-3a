import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import UserSession

pytestmark = pytest.mark.django_db


def test_register_creates_user(api_client):
    response = api_client.post(
        "/api/auth/register",
        {"username": "newperson", "email": "newperson@example.com", "password": "strongpass123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username="newperson").exists()


def test_register_rejects_short_password(api_client):
    response = api_client.post(
        "/api/auth/register",
        {"username": "newperson", "email": "newperson@example.com", "password": "short"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_returns_token_and_logs_session(api_client, user):
    response = api_client.post(
        "/api/auth/login", {"username": "rohith", "password": "strongpass123"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert "token" in response.data
    assert UserSession.objects.filter(user=user, token=response.data["token"]).exists()


def test_login_rejects_wrong_password(api_client, user):
    response = api_client.post("/api/auth/login", {"username": "rohith", "password": "wrongpass"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_rejects_common_password(api_client):
    response = api_client.post(
        "/api/auth/register",
        {"username": "newperson", "email": "newperson@example.com", "password": "password"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_is_throttled_after_too_many_attempts(api_client, user):
    for _ in range(5):
        response = api_client.post(
            "/api/auth/login", {"username": "rohith", "password": "strongpass123"}
        )
        assert response.status_code == status.HTTP_200_OK

    response = api_client.post(
        "/api/auth/login", {"username": "rohith", "password": "strongpass123"}
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_logout_ends_session_and_clears_token(auth_client, user):
    login_response = auth_client.post(
        "/api/auth/login", {"username": "rohith", "password": "strongpass123"}
    )
    assert login_response.status_code == status.HTTP_200_OK

    response = auth_client.post("/api/auth/logout")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    session = UserSession.objects.get(user=user)
    assert session.expires_at is not None
    assert not session.is_active
    assert not Token.objects.filter(user=user).exists()
    assert auth_client.get("/api/documents").status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_requires_authentication(api_client):
    response = api_client.post("/api/auth/logout")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_repeated_login_reuses_the_open_session(api_client, user):
    for _ in range(3):
        response = api_client.post(
            "/api/auth/login", {"username": "rohith", "password": "strongpass123"}
        )
        assert response.status_code == status.HTTP_200_OK

    assert UserSession.objects.filter(user=user, expires_at__isnull=True).count() == 1


def test_login_after_logout_opens_a_new_session(api_client, user):
    api_client.post("/api/auth/login", {"username": "rohith", "password": "strongpass123"})
    first_token = Token.objects.get(user=user).key
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {first_token}")
    api_client.post("/api/auth/logout")

    api_client.credentials()
    api_client.post("/api/auth/login", {"username": "rohith", "password": "strongpass123"})

    assert UserSession.objects.filter(user=user).count() == 2
    assert UserSession.objects.filter(user=user, expires_at__isnull=True).count() == 1


def test_register_rejects_duplicate_email(api_client, user):
    response = api_client.post(
        "/api/auth/register",
        {"username": "someoneelse", "email": "rohith@example.com", "password": "strongpass123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data
