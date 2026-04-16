from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.models.mercadolibre_token import MercadoLibreToken
from aiecommerce.services.mercadolibre_impl.exceptions import MLTokenError
from aiecommerce.tasks.mercadolibre_pictures import (
    _get_production_access_token,
    update_ml_listing_pictures_task,
)
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductMasterFactory

pytestmark = pytest.mark.django_db


def _make_production_token(user_id: str = "user1") -> MercadoLibreToken:
    return MercadoLibreToken.objects.create(
        user_id=user_id,
        access_token="old_token",
        refresh_token="refresh_token",
        expires_at=timezone.now(),
        is_test_user=False,
    )


class TestGetProductionAccessToken:
    def test_raises_when_no_production_token_exists(self) -> None:
        with pytest.raises(MLTokenError, match="No production Mercado Libre token found"):
            _get_production_access_token()

    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibreAuthService")
    def test_returns_refreshed_access_token(self, MockAuthService: MagicMock) -> None:
        token = _make_production_token("prod-user")
        refreshed = MagicMock()
        refreshed.access_token = "fresh_token"
        MockAuthService.return_value.get_valid_token.return_value = refreshed

        result = _get_production_access_token()

        assert result == "fresh_token"
        MockAuthService.return_value.get_valid_token.assert_called_once_with(user_id=token.user_id)

    def test_ignores_test_user_tokens(self) -> None:
        MercadoLibreToken.objects.create(
            user_id="test-user",
            access_token="test_token",
            refresh_token="refresh",
            expires_at=timezone.now(),
            is_test_user=True,
        )
        with pytest.raises(MLTokenError):
            _get_production_access_token()


class TestUpdateMlListingPicturesTask:
    def test_no_active_listing_returns_early(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("WARNING")

        update_ml_listing_pictures_task("NONEXISTENT")

        assert "No ACTIVE MercadoLibreListing" in caplog.text

    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibrePictureUpdateService")
    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibreClient")
    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibreAuthService")
    def test_success_fetches_token_and_calls_update_pictures(
        self,
        MockAuthService: MagicMock,
        MockClient: MagicMock,
        MockService: MagicMock,
    ) -> None:
        product = ProductMasterFactory(code="PROD-1")
        listing = MercadoLibreListingFactory(
            product_master=product,
            status=MercadoLibreListing.Status.ACTIVE,
        )
        _make_production_token("prod-user")
        refreshed = MagicMock()
        refreshed.access_token = "valid_token"
        MockAuthService.return_value.get_valid_token.return_value = refreshed

        update_ml_listing_pictures_task("PROD-1")

        MockClient.assert_called_once_with(access_token="valid_token")
        MockService.assert_called_once_with(ml_client=MockClient.return_value)
        MockService.return_value.update_pictures.assert_called_once_with(listing)

    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibrePictureUpdateService")
    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibreClient")
    @patch("aiecommerce.tasks.mercadolibre_pictures.MercadoLibreAuthService")
    def test_inactive_listing_is_not_found(
        self,
        MockAuthService: MagicMock,
        MockClient: MagicMock,
        MockService: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        product = ProductMasterFactory(code="PENDING-1")
        MercadoLibreListingFactory(product_master=product, status=MercadoLibreListing.Status.PENDING)
        caplog.set_level("WARNING")

        update_ml_listing_pictures_task("PENDING-1")

        MockService.return_value.update_pictures.assert_not_called()
        assert "No ACTIVE MercadoLibreListing" in caplog.text
