from unittest.mock import MagicMock

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.error_remediation_service import (
    CLASSIFICATION_GTIN,
    CLASSIFICATION_OTHER,
    CLASSIFICATION_PRICE,
    MercadoLibreErrorRemediationService,
    classify_sync_error,
)
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductMasterFactory


class TestClassifySyncError:
    @pytest.mark.parametrize(
        "sync_error,expected",
        [
            ("HTTP Error 400: item.attribute.product_identifier.invalid_format — GTIN fails checksum", CLASSIFICATION_GTIN),
            ("cause: item.attribute.invalid_product_identifier", CLASSIFICATION_GTIN),
            ("item.attribute.missing_conditional_required: GTIN is required", CLASSIFICATION_GTIN),
            ("item.price.invalid", CLASSIFICATION_PRICE),
            ("item.attributes.missing_required: LINE, COMPATIBLE_SOCKETS", CLASSIFICATION_OTHER),
            ("body.invalid_field_types", CLASSIFICATION_OTHER),
            ("item.attribute.invalid: MODEL could not be resolved", CLASSIFICATION_OTHER),
            ("", CLASSIFICATION_OTHER),
            (None, CLASSIFICATION_OTHER),
        ],
    )
    def test_classification(self, sync_error: str | None, expected: str) -> None:
        assert classify_sync_error(sync_error) == expected

    def test_missing_conditional_required_without_gtin_is_other(self) -> None:
        # If the conditional-required error is about something else (not GTIN),
        # it should not be classified as a GTIN error.
        assert classify_sync_error("item.attribute.missing_conditional_required: BRAND is required") == CLASSIFICATION_OTHER


@pytest.fixture
def ml_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(ml_client: MagicMock) -> MercadoLibreErrorRemediationService:
    return MercadoLibreErrorRemediationService(ml_client=ml_client)


@pytest.mark.django_db
class TestMercadoLibreErrorRemediationService:
    def test_gtin_error_clears_gtin_and_deletes_listing(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(gtin="1234567890123", gtin_source="google_search")
        listing = MercadoLibreListingFactory(
            product_master=product,
            status=MercadoLibreListing.Status.ERROR,
            sync_error="HTTP 400: item.attribute.product_identifier.invalid_format",
            ml_id="ML-ERR-1",
        )

        stats = service.remediate_all()

        assert stats["gtin"] == 1
        assert stats["price"] == 0
        assert stats["other"] == 0
        assert stats["total"] == 1
        ml_client.put.assert_called_once_with("items/ML-ERR-1", json={"status": "closed"})
        product.refresh_from_db()
        assert product.gtin is None
        assert product.gtin_source is None
        assert not MercadoLibreListing.objects.filter(pk=listing.pk).exists()

    def test_gtin_error_without_ml_id_just_deletes_locally(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(gtin="1234567890123")
        listing = MercadoLibreListingFactory(
            product_master=product,
            status=MercadoLibreListing.Status.ERROR,
            sync_error="item.attribute.invalid_product_identifier",
            ml_id=None,
        )

        stats = service.remediate_all()

        assert stats["gtin"] == 1
        ml_client.put.assert_not_called()
        product.refresh_from_db()
        assert product.gtin is None
        assert not MercadoLibreListing.objects.filter(pk=listing.pk).exists()

    def test_price_error_deletes_listing_without_touching_product(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(gtin="9999999999999", gtin_source="ean_api", price=100)
        listing = MercadoLibreListingFactory(
            product_master=product,
            status=MercadoLibreListing.Status.ERROR,
            sync_error="item.price.invalid",
            ml_id="ML-P-1",
        )

        stats = service.remediate_all()

        assert stats["price"] == 1
        ml_client.put.assert_called_once_with("items/ML-P-1", json={"status": "closed"})
        product.refresh_from_db()
        assert product.gtin == "9999999999999"
        assert product.price == 100
        assert not MercadoLibreListing.objects.filter(pk=listing.pk).exists()

    def test_other_error_deletes_listing(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        listing = MercadoLibreListingFactory(
            status=MercadoLibreListing.Status.ERROR,
            sync_error="item.attributes.missing_required: DISPLAY_SIZE, PROCESSOR_LINE",
            ml_id="ML-O-1",
        )

        stats = service.remediate_all()

        assert stats["other"] == 1
        ml_client.put.assert_called_once_with("items/ML-O-1", json={"status": "closed"})
        assert not MercadoLibreListing.objects.filter(pk=listing.pk).exists()

    def test_dry_run_makes_no_changes(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(gtin="1234567890123")
        listing = MercadoLibreListingFactory(
            product_master=product,
            status=MercadoLibreListing.Status.ERROR,
            sync_error="item.attribute.product_identifier.invalid_format",
            ml_id="ML-D-1",
        )

        stats = service.remediate_all(dry_run=True)

        assert stats["gtin"] == 1
        ml_client.put.assert_not_called()
        product.refresh_from_db()
        assert product.gtin == "1234567890123"
        assert MercadoLibreListing.objects.filter(pk=listing.pk).exists()

    def test_skips_non_error_listings(self, service: MercadoLibreErrorRemediationService) -> None:
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.ACTIVE, sync_error="item.price.invalid")
        MercadoLibreListingFactory(status=MercadoLibreListing.Status.PENDING, sync_error="item.price.invalid")

        stats = service.remediate_all()

        assert stats["total"] == 0

    def test_limit_caps_processing(self, service: MercadoLibreErrorRemediationService) -> None:
        for _ in range(3):
            MercadoLibreListingFactory(
                status=MercadoLibreListing.Status.ERROR,
                sync_error="item.attributes.missing_required",
                ml_id=None,
            )

        stats = service.remediate_all(limit=2)

        assert stats["total"] == 2
        assert MercadoLibreListing.objects.filter(status=MercadoLibreListing.Status.ERROR).count() == 1

    def test_close_failure_falls_back_to_local_delete(self, service: MercadoLibreErrorRemediationService, ml_client: MagicMock) -> None:
        ml_client.put.side_effect = Exception("ML unreachable")

        listing = MercadoLibreListingFactory(
            status=MercadoLibreListing.Status.ERROR,
            sync_error="item.attributes.missing_required",
            ml_id="ML-X-1",
        )

        stats = service.remediate_all()

        assert stats["other"] == 1
        assert not MercadoLibreListing.objects.filter(pk=listing.pk).exists()
