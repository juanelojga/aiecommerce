import io
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.models import MercadoLibreListing, MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError


@pytest.fixture
def mock_auth_service(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.close_ml_listings.MercadoLibreAuthService",
        MagicMock(return_value=mock),
    )
    return mock


@pytest.fixture
def mock_token_model(monkeypatch):
    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreToken.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.close_ml_listings.MercadoLibreToken", mock)
    return mock


@pytest.fixture
def mock_listing_model(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("aiecommerce.management.commands.close_ml_listings.MercadoLibreListing", mock)
    return mock


@pytest.fixture
def mock_close_service(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.close_ml_listings.MercadoLibreClosePublicationService",
        MagicMock(return_value=mock_instance),
    )
    monkeypatch.setattr(
        "aiecommerce.management.commands.close_ml_listings.MercadoLibreClient",
        MagicMock(),
    )
    return mock_instance


def test_close_ml_listings_no_token(mock_token_model, mock_auth_service):
    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    with pytest.raises(CommandError) as excinfo:
        call_command("close_ml_listings")

    assert "No token found for site MEC. Please authenticate first." in str(excinfo.value)


def test_close_ml_listings_token_error(mock_token_model, mock_auth_service):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid token")

    with pytest.raises(CommandError) as excinfo:
        call_command("close_ml_listings")

    assert "Error retrieving valid token for site MEC: Invalid token" in str(excinfo.value)


def test_close_ml_listings_success_with_id(mock_token_model, mock_auth_service, mock_listing_model, mock_close_service):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock(spec=MercadoLibreListing)
    mock_listing.ml_id = "ML-123"
    mock_listing.id = 1
    # Mocking the filter chain for listing
    mock_listing_model.objects.filter.return_value.first.return_value = mock_listing

    mock_close_service.close_listing.return_value = True

    out = io.StringIO()
    call_command("close_ml_listings", "--id", "ML-123", stdout=out)

    output = out.getvalue()
    assert "Closing listing: ML-123" in output
    assert "Listing ML-123 closed successfully." in output
    mock_close_service.close_listing.assert_called_once_with(mock_listing, dry_run=False)


def test_close_ml_listings_id_not_found(mock_token_model, mock_auth_service, mock_listing_model, mock_close_service):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing_model.objects.filter.return_value.first.return_value = None

    out = io.StringIO()
    call_command("close_ml_listings", "--id", "non-existent", stdout=out)

    output = out.getvalue()
    assert "Listing with id non-existent not found." in output
    mock_close_service.close_listing.assert_not_called()


def test_close_ml_listings_success_without_id(mock_token_model, mock_auth_service, mock_close_service):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    out = io.StringIO()
    call_command("close_ml_listings", "--hours", "24", stdout=out)

    output = out.getvalue()
    assert "Closing all paused listings older than 24 hours." in output
    mock_close_service.close_all_paused_listings.assert_called_once_with(hours=24, dry_run=False)


def test_close_ml_listings_dry_run(mock_token_model, mock_auth_service, mock_close_service):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    out = io.StringIO()
    call_command("close_ml_listings", "--dry-run", stdout=out)

    output = out.getvalue()
    assert "Performing a dry run." in output
    mock_close_service.close_all_paused_listings.assert_called_once_with(hours=48, dry_run=True)


def test_close_ml_listings_with_id_no_changes(mock_token_model, mock_auth_service, mock_listing_model, mock_close_service):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock(spec=MercadoLibreListing)
    mock_listing.ml_id = "ML-123"
    mock_listing_model.objects.filter.return_value.first.return_value = mock_listing

    mock_close_service.close_listing.return_value = False

    out = io.StringIO()
    call_command("close_ml_listings", "--id", "ML-123", stdout=out)

    output = out.getvalue()
    assert "No changes for listing ML-123." in output
