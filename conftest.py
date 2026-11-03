import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def isolated_media_root(settings, tmp_path):
    """Uploads in tests would otherwise land in the real media/ directory and pile up
    across runs. Each test gets a throwaway root."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Throttle counters live in the cache rather than the database, so they survive
    the per-test transaction rollback and leak between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="rohith", email="rohith@example.com", password="strongpass123"
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        username="priya", email="priya@example.com", password="strongpass123"
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    token, _ = Token.objects.get_or_create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client
