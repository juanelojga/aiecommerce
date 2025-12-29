from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone
from model_bakery import baker

from aiecommerce.models import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.auth_service import MercadoLibreAuthService
from aiecommerce.services.mercadolibre_impl.exceptions import (
    MLTokenError,
    MLTokenRefreshError,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def auth_service(mock_client):
    return MercadoLibreAuthService(client=mock_client)


def test_get_valid_token_existing_valid(auth_service):
    token = baker.make(MercadoLibreToken, user_id="user1", expires_at=timezone.now() + timedelta(hours=1))

    result = auth_service.get_valid_token("user1")

    assert result.user_id == "user1"
    assert result.pk == token.pk
    auth_service.client.refresh_token.assert_not_called()


def test_get_valid_token_expired_refreshes(auth_service, mock_client):
    baker.make(
        MercadoLibreToken,
        user_id="user1",
        refresh_token="old_refresh",
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    mock_client.refresh_token.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 21600,
        "user_id": "user1",
    }

    result = auth_service.get_valid_token("user1")

    assert result.access_token == "new_access"
    assert result.refresh_token == "new_refresh"
    mock_client.refresh_token.assert_called_once_with("old_refresh")


def test_get_valid_token_not_found(auth_service):
    with pytest.raises(MLTokenError, match="No token record for user_id: unknown"):
        auth_service.get_valid_token("unknown")


def test_refresh_token_validation_error(auth_service, mock_client):
    token = baker.make(MercadoLibreToken, user_id="user1", refresh_token="old_refresh")
    mock_client.refresh_token.return_value = {
        "access_token": "new_access"
        # missing other fields
    }

    with pytest.raises(MLTokenRefreshError, match="Token refresh failed for user user1"):
        auth_service.refresh_token_for_user(token)


def test_init_token_from_code_success(auth_service, mock_client):
    mock_client.exchange_code_for_token.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 21600,
        "user_id": "user2",
    }

    result = auth_service.init_token_from_code("some_code", "some_uri")

    assert result.user_id == "user2"
    assert result.access_token == "access"
    assert MercadoLibreToken.objects.filter(user_id="user2").exists()


def test_clock_injection():
    mock_clock = MagicMock()
    mock_clock.now.return_value = timezone.now()
    service = MercadoLibreAuthService(clock=mock_clock)

    token = baker.make(MercadoLibreToken, expires_at=mock_clock.now() + timedelta(hours=1))

    # This should call mock_clock.now()
    service._is_token_expired(token)

    assert mock_clock.now.called
