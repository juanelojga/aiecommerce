from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.picture_update_service import (
    GENERIC_IMAGE_SUFFIX,
    MercadoLibrePictureUpdateService,
)
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductImageFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def ml_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(ml_client: MagicMock) -> MercadoLibrePictureUpdateService:
    return MercadoLibrePictureUpdateService(ml_client=ml_client)


class TestMercadoLibrePictureUpdateService:
    def test_skip_when_no_ml_id(self, service: MercadoLibrePictureUpdateService, ml_client: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        listing = MercadoLibreListingFactory(ml_id=None)
        caplog.set_level("WARNING")

        service.update_pictures(listing)

        ml_client.put.assert_not_called()
        assert "has no ml_id" in caplog.text

    def test_skip_when_no_images(self, service: MercadoLibrePictureUpdateService, ml_client: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        listing = MercadoLibreListingFactory(ml_id="MLB123", status=MercadoLibreListing.Status.ACTIVE)
        caplog.set_level("WARNING")

        service.update_pictures(listing)

        ml_client.put.assert_not_called()
        assert "has no ProductImage rows" in caplog.text

    def test_skip_when_generic_image_present(self, service: MercadoLibrePictureUpdateService, ml_client: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        listing = MercadoLibreListingFactory(ml_id="MLB456", status=MercadoLibreListing.Status.ACTIVE)
        ProductImageFactory(
            product=listing.product_master,
            url=f"https://example.com/{GENERIC_IMAGE_SUFFIX}",
        )
        caplog.set_level("WARNING")

        service.update_pictures(listing)

        ml_client.put.assert_not_called()
        assert "still has a generic" in caplog.text

    def test_success_calls_api_and_updates_listing(self, service: MercadoLibrePictureUpdateService, ml_client: MagicMock) -> None:
        listing = MercadoLibreListingFactory(ml_id="MLB789", status=MercadoLibreListing.Status.ACTIVE)
        img1 = ProductImageFactory(product=listing.product_master, url="https://cdn.example.com/img1.jpg", order=0)
        img2 = ProductImageFactory(product=listing.product_master, url="https://cdn.example.com/img2.jpg", order=1)

        service.update_pictures(listing)

        ml_client.put.assert_called_once_with(
            "items/MLB789",
            json={"pictures": [{"source": img1.url}, {"source": img2.url}]},
        )
        listing.refresh_from_db()
        assert listing.last_synced is not None
        assert listing.sync_error is None

    def test_api_error_sets_status_to_error_and_reraises(self, service: MercadoLibrePictureUpdateService, ml_client: MagicMock) -> None:
        listing = MercadoLibreListingFactory(ml_id="MLB999", status=MercadoLibreListing.Status.ACTIVE)
        ProductImageFactory(product=listing.product_master, url="https://cdn.example.com/img.jpg")
        ml_client.put.side_effect = Exception("API down")

        with pytest.raises(Exception, match="API down"):
            service.update_pictures(listing)

        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert listing.sync_error is not None
        assert "Picture update failed" in listing.sync_error
