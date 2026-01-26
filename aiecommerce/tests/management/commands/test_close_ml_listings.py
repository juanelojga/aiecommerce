import io
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.models import MercadoLibreToken
from aiecommerce.models.mercadolibre import MercadoLibreListing
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
    mock.DoesNotExist = MercadoLibreListing.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.close_ml_listings.MercadoLibreListing", mock)
    return mock


@pytest.fixture
def mock_close_service(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.close_ml_listings.MercadoLibreClosePublicationService",
        MagicMock(return_value=mock_instance),
    )
    return mock_instance


@pytest.fixture
def mock_client(monkeypatch):
    monkeypatch.setattr(
        "aiecommerce.management.commands.close_ml_listings.MercadoLibreClient",
        MagicMock(),
    )


def test_close_all_listings_success(
    mock_token_model,
    mock_auth_service,
    mock_close_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    out = io.StringIO()
    call_command("close_ml_listings", stdout=out)

    output = out.getvalue()
    assert "Starting Mercado Libre listings closure..." in output
    assert "Closing all active listings without stock." in output
    assert "Listing closure finished." in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_token_model.objects.filter.return_value.latest.assert_called_once_with("created_at")
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")
    mock_close_service.remove_all_listings.assert_called_once_with(dry_run=False)


def test_close_all_listings_dry_run(
    mock_token_model,
    mock_auth_service,
    mock_close_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    out = io.StringIO()
    call_command("close_ml_listings", "--dry-run", stdout=out)

    output = out.getvalue()
    assert "Performing a dry run." in output
    mock_close_service.remove_all_listings.assert_called_once_with(dry_run=True)


def test_close_listing_by_pk_success(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_close_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock()
    mock_listing.id = 10
    mock_listing.ml_id = "MLC123"
    mock_listing_model.objects.filter.return_value.first.return_value = mock_listing
    mock_close_service.remove_listing.return_value = True

    out = io.StringIO()
    call_command("close_ml_listings", "--id=10", stdout=out)

    output = out.getvalue()
    assert "Closing listing: MLC123" in output
    assert "Listing MLC123 closed successfully." in output
    mock_listing_model.objects.filter.assert_called_once_with(pk="10")
    mock_close_service.remove_listing.assert_called_once_with(mock_listing, dry_run=False)


def test_close_listing_by_ml_id_success(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_close_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    pk_queryset = MagicMock()
    pk_queryset.first.return_value = None
    ml_queryset = MagicMock()
    ml_queryset.first.return_value = MagicMock(id=5, ml_id="MLC555")
    mock_listing_model.objects.filter.side_effect = [pk_queryset, ml_queryset]

    mock_close_service.remove_listing.return_value = False

    out = io.StringIO()
    call_command("close_ml_listings", "--id=MLC555", stdout=out)

    output = out.getvalue()
    assert "Closing listing: MLC555" in output
    assert "No changes for listing MLC555." in output
    assert mock_listing_model.objects.filter.call_count == 2
    mock_listing_model.objects.filter.assert_any_call(pk="MLC555")
    mock_listing_model.objects.filter.assert_any_call(ml_id="MLC555")


def test_close_listing_not_found(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_close_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    pk_queryset = MagicMock()
    pk_queryset.first.return_value = None
    ml_queryset = MagicMock()
    ml_queryset.first.return_value = None
    mock_listing_model.objects.filter.side_effect = [pk_queryset, ml_queryset]

    out = io.StringIO()
    call_command("close_ml_listings", "--id=NONEXISTENT", stdout=out)

    output = out.getvalue()
    assert "Listing with id NONEXISTENT not found." in output
    mock_close_service.remove_listing.assert_not_called()


def test_close_no_token(mock_token_model, mock_auth_service):
    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    with pytest.raises(CommandError) as excinfo:
        call_command("close_ml_listings")

    assert "No token found for site MEC. Please authenticate first." in str(excinfo.value)


def test_close_token_error(mock_token_model, mock_auth_service):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid refresh token")

    with pytest.raises(CommandError) as excinfo:
        call_command("close_ml_listings")

    assert "Error retrieving valid token for site MEC: Invalid refresh token" in str(excinfo.value)
