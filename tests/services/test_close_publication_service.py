import logging
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.close_publication_service import (
    MercadoLibreClosePublicationService,
)


def test_close_listing_without_ml_id_logs_and_skips(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = None
    listing.pk = 123

    with caplog.at_level(logging.WARNING):
        result = service.close_listing(listing)

    assert result is False
    ml_client.put.assert_not_called()
    listing.delete.assert_not_called()
    assert "has no Mercado Libre id; skipping" in caplog.text


def test_close_listing_dry_run_logs_and_returns_true(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MLC123"

    with caplog.at_level(logging.INFO):
        result = service.close_listing(listing, dry_run=True)

    assert result is True
    ml_client.put.assert_not_called()
    listing.delete.assert_not_called()
    assert "Dry run: would close listing MLC123." in caplog.text


def test_close_listing_success(caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MLC123"

    with caplog.at_level(logging.INFO):
        result = service.close_listing(listing)

    assert result is True
    ml_client.put.assert_called_once_with("items/MLC123", json={"status": "closed"})
    listing.delete.assert_called_once()
    assert "Closed listing MLC123 on Mercado Libre and removed from database." in caplog.text


def test_close_listing_handles_client_failure(caplog):
    ml_client = MagicMock()
    ml_client.put.side_effect = Exception("API error")
    service = MercadoLibreClosePublicationService(ml_client)
    listing = MagicMock()
    listing.ml_id = "MLC123"

    with caplog.at_level(logging.ERROR):
        result = service.close_listing(listing)

    assert result is False
    listing.delete.assert_not_called()
    assert "Failed to close listing MLC123." in caplog.text


def test_close_all_paused_listings_filters_and_counts(monkeypatch, caplog):
    ml_client = MagicMock()
    service = MercadoLibreClosePublicationService(ml_client)

    listing_1 = MagicMock()
    listing_2 = MagicMock()

    mock_filter = MagicMock(return_value=[listing_1, listing_2])
    monkeypatch.setattr(
        "aiecommerce.services.mercadolibre_publisher_impl.close_publication_service.MercadoLibreListing.objects.filter",
        mock_filter,
    )

    close_listing_mock = MagicMock(side_effect=[True, False])
    monkeypatch.setattr(service, "close_listing", close_listing_mock)

    # We need to mock timezone.now to have a predictable cutoff_time
    now = timezone.now()
    with patch("django.utils.timezone.now", return_value=now):
        with caplog.at_level(logging.INFO):
            service.close_all_paused_listings(hours=24, dry_run=True)

    cutoff_time = now - timedelta(hours=24)
    mock_filter.assert_called_once_with(
        status=MercadoLibreListing.Status.PAUSED,
        updated_at__lte=cutoff_time,
    )

    assert close_listing_mock.call_count == 2
    close_listing_mock.assert_any_call(listing_1, True)
    close_listing_mock.assert_any_call(listing_2, True)

    assert "Close operation finished. Closed: 1, Failed: 1." in caplog.text
