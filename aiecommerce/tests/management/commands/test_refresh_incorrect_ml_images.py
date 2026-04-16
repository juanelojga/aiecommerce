from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.management import call_command

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.picture_update_service import GENERIC_IMAGE_SUFFIX
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductImageFactory, ProductMasterFactory

pytestmark = pytest.mark.django_db

_MODULE = "aiecommerce.management.commands.refresh_incorrect_ml_images"


def _make_listing_with_generic_image(code: str = "PROD-1") -> MercadoLibreListing:
    product = ProductMasterFactory(code=code)
    ProductImageFactory(product=product, url=f"https://example.com/{GENERIC_IMAGE_SUFFIX}")
    return MercadoLibreListingFactory(
        product_master=product,
        status=MercadoLibreListing.Status.ACTIVE,
    )


class TestRefreshIncorrectMlImagesCommand:
    def test_no_listings_prints_success_and_exits(self, capsys: pytest.CaptureFixture) -> None:
        call_command("refresh_incorrect_ml_images")
        assert "No ACTIVE listings" in capsys.readouterr().out

    @patch(f"{_MODULE}.refresh_product_images")
    def test_dry_run_prints_without_calling_refresh(self, mock_refresh: object, capsys: pytest.CaptureFixture) -> None:
        _make_listing_with_generic_image("DRY-1")

        call_command("refresh_incorrect_ml_images", "--dry-run")

        mock_refresh.assert_not_called()  # type: ignore[attr-defined]
        out = capsys.readouterr().out
        assert "dry-run" in out.lower()

    @patch(f"{_MODULE}.send_telegram_notification")
    @patch(f"{_MODULE}.refresh_product_images")
    def test_real_run_queues_refresh_and_sends_notification(self, mock_refresh: object, mock_notify: object) -> None:
        _make_listing_with_generic_image("REAL-1")

        call_command("refresh_incorrect_ml_images")

        mock_refresh.assert_called_once()  # type: ignore[attr-defined]
        call_args = mock_refresh.call_args  # type: ignore[attr-defined]
        assert call_args.args[0] == "REAL-1"
        assert call_args.kwargs.get("link") is not None
        mock_notify.apply_async.assert_called_once()  # type: ignore[attr-defined]

    @patch(f"{_MODULE}.refresh_product_images")
    def test_limit_caps_number_of_queued_listings(self, mock_refresh: object) -> None:
        for i in range(3):
            _make_listing_with_generic_image(f"LIM-{i}")

        call_command("refresh_incorrect_ml_images", "--limit", "1")

        assert mock_refresh.call_count == 1  # type: ignore[attr-defined]

    @patch(f"{_MODULE}.send_telegram_notification")
    @patch(f"{_MODULE}.refresh_product_images")
    def test_skip_listing_with_empty_product_code(self, mock_refresh: object, mock_notify: object) -> None:
        product = ProductMasterFactory(code="")
        ProductImageFactory(product=product, url=f"https://example.com/{GENERIC_IMAGE_SUFFIX}")
        MercadoLibreListingFactory(product_master=product, status=MercadoLibreListing.Status.ACTIVE)

        call_command("refresh_incorrect_ml_images")

        # Refresh is never called for skipped listings
        mock_refresh.assert_not_called()  # type: ignore[attr-defined]
        # Notification IS sent because skipped > 0
        mock_notify.apply_async.assert_called_once()  # type: ignore[attr-defined]

    @patch(f"{_MODULE}.send_telegram_notification")
    @patch(f"{_MODULE}.refresh_product_images")
    def test_telegram_error_is_swallowed(self, mock_refresh: object, mock_notify: object, caplog: pytest.LogCaptureFixture) -> None:
        _make_listing_with_generic_image("TG-1")
        mock_notify.apply_async.side_effect = Exception("Telegram down")  # type: ignore[attr-defined]
        caplog.set_level("ERROR")

        call_command("refresh_incorrect_ml_images")

        assert "Failed to queue Telegram notification" in caplog.text
