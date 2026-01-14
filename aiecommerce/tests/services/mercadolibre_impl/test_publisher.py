from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.models.product import ProductImage, ProductMaster
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError
from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService


@pytest.fixture
def ml_client():
    return MagicMock()


@pytest.fixture
def attribute_fixer():
    return MagicMock()


@pytest.fixture
def publisher_service(ml_client, attribute_fixer):
    return MercadoLibrePublisherService(client=ml_client, attribute_fixer=attribute_fixer)


@pytest.fixture
def product(db):
    product = ProductMaster.objects.create(code="PROD001", seo_title="Test Product SEO Title", seo_description="Test Product SEO Description")
    # Add an image
    ProductImage.objects.create(product=product, url="http://example.com/image.jpg", order=1)

    # Create listing
    MercadoLibreListing.objects.create(product_master=product, category_id="MLA1234", final_price=Decimal("100.50"), available_quantity=10, attributes=[{"id": "COLOR", "value_name": "Rojo"}])
    return product


@pytest.mark.django_db
class TestMercadoLibrePublisherService:
    def test_build_payload(self, publisher_service, product):
        payload = publisher_service.build_payload(product)

        assert payload["title"] == "Test Product SEO Title"
        assert payload["category_id"] == "MLA1234"
        assert payload["price"] == 100.5
        assert payload["currency_id"] == "USD"
        assert payload["available_quantity"] == 10
        assert payload["buying_mode"] == "buy_it_now"
        assert payload["listing_type_id"] == "bronze"
        assert payload["condition"] == "new"
        assert payload["pictures"] == [{"source": "http://example.com/image.jpg"}]
        assert payload["attributes"] == [{"id": "COLOR", "value_name": "Rojo"}]
        assert any(term["id"] == "WARRANTY_TYPE" for term in payload["sale_terms"])

    def test_build_payload_test_mode(self, publisher_service, product):
        payload = publisher_service.build_payload(product, test=True)
        assert payload["title"] == "Item de test - No ofertar"

    def test_publish_product_success(self, publisher_service, ml_client, product):
        # Mock responses
        ml_client.post.side_effect = [
            {"id": "MLA987654321"},  # Response from items POST
            {"id": "MLA987654321-desc"},  # Response from description POST (actually content doesn't matter much)
        ]

        response = publisher_service.publish_product(product)

        assert response["id"] == "MLA987654321"

        # Verify ML client calls
        assert ml_client.post.call_count == 2

        # Verify DB update
        product.refresh_from_db()
        listing = product.mercadolibre_listing
        assert listing.ml_id == "MLA987654321"
        assert listing.status == MercadoLibreListing.Status.ACTIVE
        assert listing.last_synced is not None
        assert listing.sync_error is None

    def test_publish_product_dry_run(self, publisher_service, ml_client, product):
        response = publisher_service.publish_product(product, dry_run=True)

        assert response["dry_run"] is True
        assert "payload" in response
        assert ml_client.post.call_count == 0

        # Verify DB NOT updated
        product.refresh_from_db()
        listing = product.mercadolibre_listing
        assert listing.ml_id is None
        assert listing.status == MercadoLibreListing.Status.PENDING

    def test_publish_product_api_error(self, publisher_service, ml_client, product):
        # Mock MLAPIError on the first POST
        ml_client.post.side_effect = MLAPIError("API Error")

        with pytest.raises(MLAPIError):
            publisher_service.publish_product(product)

        # Verify DB update with error
        product.refresh_from_db()
        listing = product.mercadolibre_listing
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert listing.sync_error == "API Error"
        assert listing.ml_id is None

    def test_publish_product_description_error(self, publisher_service, ml_client, product):
        # Mock success on first POST, error on second
        ml_client.post.side_effect = [{"id": "MLA987654321"}, MLAPIError("Description Error")]

        with pytest.raises(MLAPIError):
            publisher_service.publish_product(product)

        # Verify DB update with error
        product.refresh_from_db()
        listing = product.mercadolibre_listing
        assert listing.status == MercadoLibreListing.Status.ERROR
        assert listing.sync_error == "Description Error"
        # Even if items was created, we treat the whole process as failed for now
        # and it would have been rolled back if it was in an atomic block,
        # but the ML API call is external.
        # The current implementation updates DB ONLY after both API calls succeed.

    def test_publish_product_retry_with_attribute_fix(self, publisher_service, ml_client, attribute_fixer, product):
        # 1. First call to post("items", ...) fails with 400 Validation Error
        # 2. Attribute fixer is called
        # 3. Second call to post("items", ...) succeeds
        # 4. Call to post("items/MLA987654321/description", ...) succeeds

        error_msg = 'HTTP Error 400: {"cause":[{"code":"invalid_attributes"}]}'
        ml_client.post.side_effect = [
            MLAPIError(error_msg),
            {"id": "MLA987654321"},
            {"id": "MLA987654321-desc"},
        ]

        fixed_attributes = [{"id": "COLOR", "value_name": "Rojo (Fixed)"}]
        attribute_fixer.fix_attributes.return_value = fixed_attributes

        response = publisher_service.publish_product(product)

        assert response["id"] == "MLA987654321"
        assert attribute_fixer.fix_attributes.call_count == 1
        assert ml_client.post.call_count == 3

        # Verify DB update with fixed attributes
        product.refresh_from_db()
        listing = product.mercadolibre_listing
        assert listing.attributes == fixed_attributes
        assert listing.status == MercadoLibreListing.Status.ACTIVE
