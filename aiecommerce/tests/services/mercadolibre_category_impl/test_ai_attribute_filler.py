from unittest.mock import MagicMock

import pytest

from aiecommerce.services.mercadolibre_category_impl.ai_attribute_filler import (
    MercadolibreAIAttributeFiller,
    MercadolibreAttributeResponse,
    MLAttributeValue,
)
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestMercadolibreAIAttributeFiller:
    @pytest.fixture
    def mock_instructor_client(self):
        return MagicMock()

    @pytest.fixture
    def filler(self, mock_instructor_client):
        return MercadolibreAIAttributeFiller(client=mock_instructor_client)

    def test_fill_and_validate_success(self, filler, mock_instructor_client):
        # Setup
        product = ProductMasterFactory(normalized_name="Test Product", specs="Color: Red, Size: XL", gtin="1234567890123", seo_description="Best test product ever", model_name="TP-100")
        attributes = [
            {"id": "BRAND", "tags": {"required": True}},
            {"id": "MODEL", "relevance": 1},
            {"id": "COLOR", "relevance": 2},  # Should be filtered out
        ]

        # Mock AI response
        mock_response = MercadolibreAttributeResponse(
            attributes=[
                MLAttributeValue(id="BRAND", value_name="Marca de Prueba", value_id=None),
                MLAttributeValue(id="MODEL", value_name="TP-100", value_id=None),
            ]
        )
        mock_instructor_client.chat.completions.create.return_value = mock_response

        # Execute
        result = filler.fill_and_validate(product, attributes)

        # Assertions
        assert len(result) == 2
        assert result[0] == {"id": "BRAND", "value_name": "Marca de Prueba"}
        assert result[1] == {"id": "MODEL", "value_name": "TP-100"}

        # Verify client call
        args, kwargs = mock_instructor_client.chat.completions.create.call_args
        assert kwargs["response_model"] == MercadolibreAttributeResponse
        assert "Product Data: {'name': 'Test Product', 'specs': 'Color: Red, Size: XL', 'gtin': '1234567890123', 'seo_description': 'Best test product ever', 'model_name': 'TP-100'}" in kwargs["messages"][1]["content"]
        assert "Attribute Definitions: [{'id': 'BRAND', 'tags': {'required': True}}, {'id': 'MODEL', 'relevance': 1}]" in kwargs["messages"][1]["content"]

    def test_fill_and_validate_filtering(self, filler, mock_instructor_client):
        product = ProductMasterFactory()
        attributes = [
            {"id": "ATTR1", "tags": {"required": True}},
            {"id": "ATTR2", "relevance": 1},
            {"id": "ATTR3", "tags": {"required": False}, "relevance": 2},
            {"id": "ATTR4"},
        ]

        mock_instructor_client.chat.completions.create.return_value = MercadolibreAttributeResponse(attributes=[])

        filler.fill_and_validate(product, attributes)

        _, kwargs = mock_instructor_client.chat.completions.create.call_args
        # Only ATTR1 and ATTR2 should be in relevant_defs
        assert "Attribute Definitions: [{'id': 'ATTR1', 'tags': {'required': True}}, {'id': 'ATTR2', 'relevance': 1}]" in kwargs["messages"][1]["content"]

    def test_fill_and_validate_product_name_fallback(self, filler, mock_instructor_client):
        # Test that it falls back to description if normalized_name is missing
        product = ProductMasterFactory(normalized_name=None, description="Fallback Description")
        attributes: list[dict] = []

        mock_instructor_client.chat.completions.create.return_value = MercadolibreAttributeResponse(attributes=[])

        filler.fill_and_validate(product, attributes)

        _, kwargs = mock_instructor_client.chat.completions.create.call_args
        assert "'name': 'Fallback Description'" in kwargs["messages"][1]["content"]

    def test_fill_and_validate_empty_attributes(self, filler, mock_instructor_client):
        product = ProductMasterFactory()
        attributes: list[dict] = []

        mock_instructor_client.chat.completions.create.return_value = MercadolibreAttributeResponse(attributes=[])

        result = filler.fill_and_validate(product, attributes)

        assert result == []
        mock_instructor_client.chat.completions.create.assert_called_once()
