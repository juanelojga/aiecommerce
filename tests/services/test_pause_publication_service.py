import logging
from unittest.mock import MagicMock

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.pause_publication_service import (
    MercadoLibrePausePublicationService,
)


def test_pause_listing_without_ml_id_logs_and_skips(caplog):
    ml_client = MagicMock()
    service = MercadoLibrePausePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = None
    listing.pk = 123

    with caplog.at_level(logging.WARNING):
        result = service.pause_listing(listing)

    assert result is False
    ml_client.put.assert_not_called()
    listing.save.assert_not_called()
    assert "has no Mercado Libre id; skipping" in caplog.text


def test_pause_listing_dry_run_logs_and_returns_true(caplog):
    ml_client = MagicMock()
    service = MercadoLibrePausePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.INFO):
        result = service.pause_listing(listing, dry_run=True)

    assert result is True
    ml_client.put.assert_not_called()
    listing.save.assert_not_called()
    assert "Dry run: would pause listing MCO123." in caplog.text


def test_pause_listing_pauses_and_updates_status(caplog):
    ml_client = MagicMock()
    service = MercadoLibrePausePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.INFO):
        result = service.pause_listing(listing)

    assert result is True
    ml_client.put.assert_called_once_with("items/MCO123", json={"status": "paused"})
    assert listing.status == MercadoLibreListing.Status.PAUSED
    listing.save.assert_called_once_with(update_fields=["status"])
    assert "Paused listing MCO123 on Mercado Libre" in caplog.text


def test_pause_listing_handles_client_failure(caplog):
    ml_client = MagicMock()
    ml_client.put.side_effect = Exception("boom")
    service = MercadoLibrePausePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MCO123"

    with caplog.at_level(logging.ERROR):
        result = service.pause_listing(listing)

    assert result is False
    listing.save.assert_not_called()
    assert "Failed to pause listing MCO123." in caplog.text


def test_pause_all_listings_filters_and_counts(monkeypatch, caplog):
    ml_client = MagicMock()
    service = MercadoLibrePausePublicationService(ml_client)
    listing_1 = MagicMock()
    listing_2 = MagicMock()

    mock_filter = MagicMock(return_value=[listing_1, listing_2])
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.pause_publication_service.MercadoLibreListing.objects.filter",
        mock_filter,
    )
    pause_listing_mock = MagicMock(side_effect=[True, False])
    monkeypatch.setattr(service, "pause_listing", pause_listing_mock)

    with caplog.at_level(logging.INFO):
        service.pause_all_listings(dry_run=True)

    mock_filter.assert_called_once_with(status=MercadoLibreListing.Status.ACTIVE, available_quantity=0)
    pause_listing_mock.assert_any_call(listing_1, True)
    pause_listing_mock.assert_any_call(listing_2, True)
    assert "Paused: 1, Failed: 1." in caplog.text
