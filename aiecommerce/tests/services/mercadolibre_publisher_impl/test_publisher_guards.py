from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService
from aiecommerce.tests.factories import MercadoLibreListingFactory, ProductMasterFactory


@pytest.fixture
def ml_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def attribute_fixer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def publisher(ml_client: MagicMock, attribute_fixer: MagicMock) -> MercadoLibrePublisherService:
    return MercadoLibrePublisherService(client=ml_client, attribute_fixer=attribute_fixer)


class TestSanitizeAttributes:
    def test_drops_price_entry(self) -> None:
        attrs = [{"id": "BRAND", "value_name": "Asus"}, {"id": "PRICE", "value_name": "100"}]
        result = MercadoLibrePublisherService._sanitize_attributes(attrs)
        assert result == [{"id": "BRAND", "value_name": "Asus"}]

    def test_drops_invalid_gtin(self) -> None:
        attrs = [{"id": "GTIN", "value_name": "1234567890"}]  # 10 digits — invalid
        result = MercadoLibrePublisherService._sanitize_attributes(attrs)
        assert result == []

    def test_keeps_valid_gtin(self) -> None:
        # Generate a valid EAN-13
        body = "400638133393"
        digits = [int(c) for c in body]
        weighted = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
        check = (10 - (weighted % 10)) % 10
        gtin = body + str(check)
        attrs = [{"id": "GTIN", "value_name": gtin}]
        assert MercadoLibrePublisherService._sanitize_attributes(attrs) == attrs

    def test_none_input(self) -> None:
        assert MercadoLibrePublisherService._sanitize_attributes(None) == []

    def test_ignores_non_dict_entries(self) -> None:
        result = MercadoLibrePublisherService._sanitize_attributes([{"id": "BRAND"}, "garbage", 42])  # type: ignore[list-item]
        assert result == [{"id": "BRAND"}]


@pytest.mark.django_db
class TestPublisherGuards:
    def test_missing_category_id_marks_error_without_api_call(self, publisher: MercadoLibrePublisherService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(price=Decimal("100.00"))
        listing = MercadoLibreListingFactory(product_master=product, category_id=None, final_price=Decimal("120.00"))

        result = publisher.publish_product(product)

        assert result is None
        ml_client.post.assert_not_called()
        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert "category_id" in (listing.sync_error or "")

    def test_missing_final_price_without_product_price_marks_error(self, publisher: MercadoLibrePublisherService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(price=None)
        listing = MercadoLibreListingFactory(product_master=product, category_id="MEC1693", final_price=None)

        result = publisher.publish_product(product)

        assert result is None
        ml_client.post.assert_not_called()
        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert "final_price" in (listing.sync_error or "") or "price" in (listing.sync_error or "")

    def test_zero_product_price_marks_error(self, publisher: MercadoLibrePublisherService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(price=Decimal("0"))
        listing = MercadoLibreListingFactory(product_master=product, category_id="MEC1693", final_price=None)

        result = publisher.publish_product(product)

        assert result is None
        ml_client.post.assert_not_called()
        listing.refresh_from_db()
        assert listing.status == MercadoLibreListing.Status.ERROR

    def test_final_price_falls_back_to_product_price(self, publisher: MercadoLibrePublisherService, ml_client: MagicMock) -> None:
        product = ProductMasterFactory(price=Decimal("150.00"))
        listing = MercadoLibreListingFactory(
            product_master=product,
            category_id="MEC1693",
            final_price=None,
            attributes=[],
        )
        ml_client.post.return_value = {"id": "MLB-OK-1"}

        result = publisher.publish_product(product)

        assert result == {"id": "MLB-OK-1"}
        listing.refresh_from_db()
        assert listing.final_price == Decimal("150.00")
        assert listing.status == MercadoLibreListing.Status.ACTIVE
        assert listing.ml_id == "MLB-OK-1"
