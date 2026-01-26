import logging
from unittest.mock import MagicMock

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.close_publication_service import (
    MercadoLibreClosePublicationService,
)


def test_remove_listing_without_ml_id_logs_and_skips(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = None
    listing.pk = 123

    with caplog.at_level(logging.WARNING):
        result = service.remove_listing(listing)

    assert result is False
    ml_client.put.assert_not_called()
    listing.delete.assert_not_called()
    assert "has no Mercado Libre id; skipping" in caplog.text


def test_remove_listing_dry_run_logs_and_returns_true(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.INFO):
        result = service.remove_listing(listing, dry_run=True)

    assert result is True
    ml_client.put.assert_not_called()
    listing.delete.assert_not_called()
    assert "Dry run: would close listing MCO123." in caplog.text


def test_remove_listing_closes_and_deletes(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.INFO):
        result = service.remove_listing(listing)

    assert result is True
    ml_client.put.assert_called_once_with("items/MCO123", json={"status": "closed"})
    listing.delete.assert_called_once()
    assert "Closed listing MCO123 on Mercado Libre" in caplog.text


def test_remove_listing_handles_client_failure(caplog):
    ml_client = MagicMock()
    ml_client.put.side_effect = Exception("boom")
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.ERROR):
        result = service.remove_listing(listing)

    assert result is False
    listing.delete.assert_not_called()
    assert "Failed to close listing MCO123." in caplog.text


def test_remove_all_listings_filters_and_counts(monkeypatch, caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing_1 = MagicMock()
    listing_2 = MagicMock()

    mock_filter = MagicMock(return_value=[listing_1, listing_2])
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.close_publication_service.MercadoLibreListing.objects.filter",
        mock_filter,
    )
    remove_listing_mock = MagicMock(side_effect=[True, False])
    monkeypatch.setattr(service, "remove_listing", remove_listing_mock)

    with caplog.at_level(logging.INFO):
        service.remove_all_listings(dry_run=True)

    mock_filter.assert_called_once_with(status=MercadoLibreListing.Status.ACTIVE, available_quantity=0)
    remove_listing_mock.assert_any_call(listing_1, True)
    remove_listing_mock.assert_any_call(listing_2, True)
    assert "Closed: 1, Failed: 1." in caplog.text
