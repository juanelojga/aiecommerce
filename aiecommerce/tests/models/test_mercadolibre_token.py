from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone
from model_bakery import baker

from aiecommerce.models.mercadolibre_token import MercadoLibreToken

pytestmark = pytest.mark.django_db


def test_mercadolibre_token_creation():
    """Test that a MercadoLibreToken can be created with all fields."""
    expires_at = timezone.now() + timedelta(hours=6)
    token = baker.make(
        MercadoLibreToken, user_id="123456", access_token="APP_USR-access-token", refresh_token="TG-refresh-token", expires_at=expires_at
    )

    assert token.user_id == "123456"
    assert token.access_token == "APP_USR-access-token"
    assert token.refresh_token == "TG-refresh-token"
    assert token.expires_at == expires_at
    assert token.created_at is not None
    assert token.updated_at is not None


def test_mercadolibre_token_str_representation():
    """Test the string representation of MercadoLibreToken."""
    token = baker.make(MercadoLibreToken, user_id="7890")
    assert str(token) == "ML Token - User ID: 7890"


def test_mercadolibre_token_is_expired_true():
    """Test is_expired returns True when the token is past its expiration."""
    # Already expired 10 minutes ago
    expires_at = timezone.now() - timedelta(minutes=10)
    token = baker.make(MercadoLibreToken, expires_at=expires_at)
    assert token.is_expired() is True


def test_mercadolibre_token_is_expired_close_to_expiration():
    """Test is_expired returns True when the token is close to expiring (within 5 minutes)."""
    # Expiring in 2 minutes
    expires_at = timezone.now() + timedelta(minutes=2)
    token = baker.make(MercadoLibreToken, expires_at=expires_at)
    assert token.is_expired() is True


def test_mercadolibre_token_is_expired_false():
    """Test is_expired returns False when the token is not expired."""
    # Expiring in 1 hour
    expires_at = timezone.now() + timedelta(hours=1)
    token = baker.make(MercadoLibreToken, expires_at=expires_at)
    assert token.is_expired() is False


def test_mercadolibre_token_unique_user_id():
    """Test that user_id must be unique."""
    baker.make(MercadoLibreToken, user_id="unique_user")
    with pytest.raises(IntegrityError):
        baker.make(MercadoLibreToken, user_id="unique_user")
