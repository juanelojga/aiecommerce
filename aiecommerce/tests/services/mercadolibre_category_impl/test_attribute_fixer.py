from typing import Any
from unittest.mock import MagicMock

import pytest
from django.conf import settings

from aiecommerce.services.mercadolibre_category_impl.ai_attribute_filler import MLAttributeValue
from aiecommerce.services.mercadolibre_category_impl.attribute_fixer import (
    MercadolibreAttributeFixer,
    MercadolibreAttributeFixResponse,
)
from aiecommerce.tests.factories import ProductMasterFactory


@pytest.mark.django_db
class TestMercadolibreAttributeFixer:
    @pytest.fixture
    def mock_instructor_client(self):
        return MagicMock()

    @pytest.fixture
    def fixer(self, mock_instructor_client):
        return MercadolibreAttributeFixer(client=mock_instructor_client)

    def test_fix_attributes_success(self, fixer, mock_instructor_client):
        # Setup
        product = ProductMasterFactory(normalized_name="Test Smartphone", specs="Color: Blue, RAM: 8GB, Storage: 128GB", model_name="Phone X")
        current_attributes = [{"id": "BRAND", "value_name": "Generic"}]
        error_message = "The attribute COLOR is required."

        # Mock AI response
        mock_response = MercadolibreAttributeFixResponse(
            attributes=[
                MLAttributeValue(id="BRAND", value_name="Generic", value_id=None),
                MLAttributeValue(id="COLOR", value_name="Azul", value_id=None),
            ]
        )
        mock_instructor_client.chat.completions.create.return_value = mock_response

        # Execute
        result = fixer.fix_attributes(product, current_attributes, error_message)

        # Assertions
        assert len(result) == 2
        assert any(attr["id"] == "BRAND" and attr["value_name"] == "Generic" for attr in result)
        assert any(attr["id"] == "COLOR" and attr["value_name"] == "Azul" for attr in result)

        # Verify client call
        args, kwargs = mock_instructor_client.chat.completions.create.call_args
        assert kwargs["model"] == settings.OPENROUTER_MERCADOLIBRE_ATTRIBUTE_FILLER_MODEL
        assert kwargs["response_model"] == MercadolibreAttributeFixResponse

        messages = kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "expert at fixing Mercado Libre validation errors" in messages[0]["content"]

        user_content = messages[1]["content"]
        assert f"Error Message: {error_message}" in user_content
        assert f"Current Attributes: {current_attributes}" in user_content
        assert "Test Smartphone" in user_content
        assert "Color: Blue, RAM: 8GB, Storage: 128GB" in user_content

    def test_fix_attributes_with_none_values(self, fixer, mock_instructor_client):
        # Setup
        product = ProductMasterFactory()
        current_attributes: list[dict[str, Any]] = []
        error_message = "Some error"

        # Mock AI response with some None values (should be excluded by model_dump)
        mock_response = MercadolibreAttributeFixResponse(
            attributes=[
                MLAttributeValue(id="BRAND", value_name="Brand", value_id=None),
            ]
        )
        mock_instructor_client.chat.completions.create.return_value = mock_response

        # Execute
        result = fixer.fix_attributes(product, current_attributes, error_message)

        # Assertions
        assert result == [{"id": "BRAND", "value_name": "Brand"}]
        # value_id should not be in the dict because it's None and exclude_none=True
        assert "value_id" not in result[0]
