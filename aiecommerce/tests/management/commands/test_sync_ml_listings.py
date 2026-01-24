import io
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError, call_command

from aiecommerce.models import MercadoLibreToken
from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.services.mercadolibre_publisher_impl.sync_service import MercadoLibreSyncService


@pytest.fixture
def mock_auth_service(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.sync_ml_listings.MercadoLibreAuthService",
        MagicMock(return_value=mock),
    )
    return mock


@pytest.fixture
def mock_token_model(monkeypatch):
    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreToken.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.sync_ml_listings.MercadoLibreToken", mock)
    return mock


@pytest.fixture
def mock_listing_model(monkeypatch):
    mock = MagicMock()
    mock.DoesNotExist = MercadoLibreListing.DoesNotExist
    monkeypatch.setattr("aiecommerce.management.commands.sync_ml_listings.MercadoLibreListing", mock)
    return mock


@pytest.fixture
def mock_sync_service(monkeypatch):
    mock_instance = MagicMock()
    monkeypatch.setattr(
        "aiecommerce.management.commands.sync_ml_listings.MercadoLibreSyncService",
        MagicMock(return_value=mock_instance),
    )
    return mock_instance


@pytest.fixture
def mock_client(monkeypatch):
    monkeypatch.setattr(
        "aiecommerce.management.commands.sync_ml_listings.MercadoLibreClient",
        MagicMock(),
    )


def test_sync_all_listings_success(
    mock_token_model,
    mock_auth_service,
    mock_sync_service,
    mock_client,
):
    # Setup
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Run
    out = io.StringIO()
    call_command("sync_ml_listings", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Starting Mercado Libre listings synchronization..." in output
    assert "Syncing all active listings." in output
    assert "Synchronization finished." in output

    mock_token_model.objects.filter.assert_called_with(is_test_user=False)
    mock_auth_service.get_valid_token.assert_called_once_with(user_id="user_123")
    mock_sync_service.sync_all_listings.assert_called_once_with(dry_run=False, force=False)


def test_sync_all_listings_with_force(
    mock_token_model,
    mock_auth_service,
    mock_sync_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token.user_id = "user_123"
    mock_token.access_token = "valid_token"

    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    out = io.StringIO()
    call_command("sync_ml_listings", "--force", stdout=out)

    output = out.getvalue()
    assert "Syncing all active listings." in output

    mock_sync_service.sync_all_listings.assert_called_once_with(dry_run=False, force=True)


def test_sync_single_listing_by_id_success(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_sync_service,
    mock_client,
):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock()
    mock_listing.id = 1
    mock_listing.ml_id = "MLC123"
    mock_listing_model.objects.get.side_effect = [mock_listing]
    mock_sync_service.sync_listing.return_value = True

    # Run
    out = io.StringIO()
    call_command("sync_ml_listings", "--id=1", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Syncing listing: MLC123" in output
    assert "Listing MLC123 updated." in output
    mock_listing_model.objects.get.assert_called_with(pk="1")
    mock_sync_service.sync_listing.assert_called_once_with(mock_listing, dry_run=False, force=False)


def test_sync_single_listing_by_id_with_force(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_sync_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock()
    mock_listing.id = 1
    mock_listing.ml_id = "MLC123"
    mock_listing_model.objects.get.side_effect = [mock_listing]
    mock_sync_service.sync_listing.return_value = True

    out = io.StringIO()
    call_command("sync_ml_listings", "--id=1", "--force", stdout=out)

    output = out.getvalue()
    assert "Syncing listing: MLC123" in output
    mock_sync_service.sync_listing.assert_called_once_with(mock_listing, dry_run=False, force=True)


def test_sync_single_listing_by_ml_id_success(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_sync_service,
    mock_client,
):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock()
    mock_listing.id = 1
    mock_listing.ml_id = "MLC123"

    # First attempt by PK fails, second by ml_id succeeds
    mock_listing_model.objects.get.side_effect = [
        MercadoLibreListing.DoesNotExist,
        mock_listing,
    ]
    mock_sync_service.sync_listing.return_value = False

    # Run
    out = io.StringIO()
    call_command("sync_ml_listings", "--id=MLC123", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Syncing listing: MLC123" in output
    assert "No changes for listing MLC123." in output
    assert mock_listing_model.objects.get.call_count == 2
    mock_listing_model.objects.get.assert_any_call(pk="MLC123")
    mock_listing_model.objects.get.assert_any_call(ml_id="MLC123")


def test_sync_listing_falls_back_to_ml_id_on_value_error(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_sync_service,
    mock_client,
):
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing = MagicMock()
    mock_listing.id = 1
    mock_listing.ml_id = "MLC123"
    mock_listing_model.objects.get.side_effect = [ValueError("Invalid pk"), mock_listing]

    out = io.StringIO()
    call_command("sync_ml_listings", "--id=MLC123", stdout=out)

    output = out.getvalue()
    assert "Syncing listing: MLC123" in output
    mock_listing_model.objects.get.assert_any_call(pk="MLC123")
    mock_listing_model.objects.get.assert_any_call(ml_id="MLC123")


def test_sync_dry_run(
    mock_token_model,
    mock_auth_service,
    mock_sync_service,
    mock_client,
):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    # Run
    out = io.StringIO()
    call_command("sync_ml_listings", "--dry-run", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Performing a dry run." in output
    mock_sync_service.sync_all_listings.assert_called_once_with(dry_run=True, force=False)


def test_sync_no_token(mock_token_model, mock_auth_service):
    # Setup
    mock_token_model.objects.filter.return_value.latest.side_effect = MercadoLibreToken.DoesNotExist

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("sync_ml_listings")

    assert "No token found for site MEC. Please authenticate first." in str(excinfo.value)


def test_sync_token_error(mock_token_model, mock_auth_service):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.side_effect = MLTokenError("Invalid refresh token")

    # Run & Assert
    with pytest.raises(CommandError) as excinfo:
        call_command("sync_ml_listings")

    assert "Error retrieving valid token for site MEC: Invalid refresh token" in str(excinfo.value)


def test_sync_listing_not_found(
    mock_token_model,
    mock_auth_service,
    mock_listing_model,
    mock_client,
):
    # Setup
    mock_token = MagicMock()
    mock_token_model.objects.filter.return_value.latest.return_value = mock_token
    mock_auth_service.get_valid_token.return_value = mock_token

    mock_listing_model.objects.get.side_effect = MercadoLibreListing.DoesNotExist

    # Run
    out = io.StringIO()
    call_command("sync_ml_listings", "--id=NONEXISTENT", stdout=out)

    # Assert
    output = out.getvalue()
    assert "Listing with id NONEXISTENT not found." in output


def test_sync_listing_updates_price_and_quantity(monkeypatch):
    price_engine = MagicMock()
    price_engine.calculate.return_value = {
        "final_price": Decimal("12.50"),
        "net_price": Decimal("10.00"),
        "profit": Decimal("2.50"),
    }
    stock_engine = MagicMock()
    stock_engine.get_available_quantity.return_value = 5
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibrePriceEngine",
        MagicMock(return_value=price_engine),
    )
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibreStockEngine",
        MagicMock(return_value=stock_engine),
    )

    client = MagicMock()
    service = MercadoLibreSyncService(ml_client=client)

    product_master = MagicMock()
    product_master.price = Decimal("10.00")
    product_master.is_active = True
    listing = MagicMock()
    listing.product_master = product_master
    listing.final_price = Decimal("10.00")
    listing.available_quantity = 1
    listing.ml_id = "MLC123"

    result = service.sync_listing(listing, dry_run=False)

    assert result is True
    client.put.assert_called_once_with(
        "items/MLC123",
        json={"price": 12.5, "available_quantity": 5},
    )
    assert listing.final_price == Decimal("12.50")
    assert listing.net_price == Decimal("10.00")
    assert listing.profit == Decimal("2.50")
    assert listing.available_quantity == 5
    listing.save.assert_called_once_with(
        update_fields=["final_price", "net_price", "profit", "available_quantity"],
    )


def test_sync_listing_no_changes_skips_update(monkeypatch):
    price_engine = MagicMock()
    price_engine.calculate.return_value = {
        "final_price": Decimal("10.00"),
        "net_price": Decimal("8.00"),
        "profit": Decimal("2.00"),
    }
    stock_engine = MagicMock()
    stock_engine.get_available_quantity.return_value = 3
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibrePriceEngine",
        MagicMock(return_value=price_engine),
    )
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibreStockEngine",
        MagicMock(return_value=stock_engine),
    )

    client = MagicMock()
    service = MercadoLibreSyncService(ml_client=client)

    product_master = MagicMock()
    product_master.price = Decimal("10.00")
    product_master.is_active = True
    listing = MagicMock()
    listing.product_master = product_master
    listing.final_price = Decimal("10.00")
    listing.available_quantity = 3
    listing.ml_id = "MLC999"

    result = service.sync_listing(listing, dry_run=False)

    assert result is False
    client.put.assert_not_called()
    listing.save.assert_not_called()


def test_sync_listing_dry_run_skips_client_update(monkeypatch):
    price_engine = MagicMock()
    price_engine.calculate.return_value = {
        "final_price": Decimal("15.00"),
        "net_price": Decimal("12.00"),
        "profit": Decimal("3.00"),
    }
    stock_engine = MagicMock()
    stock_engine.get_available_quantity.return_value = 2
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibrePriceEngine",
        MagicMock(return_value=price_engine),
    )
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.sync_service.MercadoLibreStockEngine",
        MagicMock(return_value=stock_engine),
    )

    client = MagicMock()
    service = MercadoLibreSyncService(ml_client=client)

    product_master = MagicMock()
    product_master.price = Decimal("10.00")
    product_master.is_active = True
    listing = MagicMock()
    listing.product_master = product_master
    listing.final_price = Decimal("10.00")
    listing.available_quantity = 1
    listing.ml_id = "MLC777"

    result = service.sync_listing(listing, dry_run=True)

    assert result is True
    client.put.assert_not_called()
    listing.save.assert_not_called()
    assert listing.final_price == Decimal("10.00")
    assert listing.available_quantity == 1
