from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from openai import APIError
from pydantic import ValidationError

from aiecommerce.services.specifications_impl.exceptions import ConfigurationError
from aiecommerce.services.specifications_impl.schemas import GenericSpecs, NotebookSpecs
from aiecommerce.services.specifications_impl.service import ProductSpecificationsService


@pytest.fixture
def mock_settings():
    with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
        yield settings


@pytest.fixture
def service(mock_settings):
    with patch("aiecommerce.services.specifications_impl.service.OpenAI"), patch("aiecommerce.services.specifications_impl.service.instructor.from_openai") as mock_instructor:
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        svc = ProductSpecificationsService()
        yield svc, mock_client


class TestProductSpecificationsService:
    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_initialization_success(self, mock_instructor, mock_openai, mock_settings):
        service = ProductSpecificationsService()

        assert service.model_name == "test-model"
        mock_openai.assert_called_once_with(base_url="https://test.url", api_key="test-key")
        mock_instructor.assert_called_once()

    def test_initialization_failure(self):
        with patch.object(settings, "OPENROUTER_API_KEY", None):
            with pytest.raises(ConfigurationError) as excinfo:
                ProductSpecificationsService()
            assert "The following settings are required" in str(excinfo.value)

    def test_enrich_product_success_generic(self, service):
        svc, mock_client = service
        expected_specs = GenericSpecs(summary="Test Product")
        mock_client.chat.completions.create.return_value = expected_specs

        product_data = {"code": "PROD1", "description": "A test product", "category": "Test"}
        result = svc.enrich_product(product_data)

        assert result == expected_specs
        mock_client.chat.completions.create.assert_called_once()
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "test-model"

        # Verify text construction
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "Code: PROD1" in user_message["content"]
        assert "Description: A test product" in user_message["content"]
        assert "Category: Test" in user_message["content"]

        # Verify system message has rules
        system_message = next(m for m in kwargs["messages"] if m["role"] == "system")
        assert "RULES FOR MODEL & NAME" in system_message["content"]
        assert "normalized_name" in system_message["content"]
        assert "model_name: Extract ONLY" in system_message["content"]
        assert "normalized_name: Construct a clean name" in system_message["content"]
        assert "Remove distributor fluff" in system_message["content"]

    def test_enrich_product_success_specific_schema(self, service):
        svc, mock_client = service
        expected_specs = NotebookSpecs(manufacturer="Dell", model_name="Latitude 5430", cpu="Intel Core i5", ram="16GB")
        mock_client.chat.completions.create.return_value = expected_specs

        result = svc.enrich_product({"description": "Dell Latitude 5430 i5 16GB"})

        assert isinstance(result, NotebookSpecs)
        assert result.manufacturer == "Dell"
        assert result.ram == "16GB"

    @pytest.mark.parametrize(
        "product_data, expected_text",
        [
            ({"code": "C1"}, "Code: C1"),
            ({"description": "D1"}, "Description: D1"),
            ({"category": "CAT1"}, "Category: CAT1"),
            ({"code": "C1", "category": "CAT1"}, "Code: C1\nCategory: CAT1"),
        ],
    )
    def test_enrich_product_partial_data(self, service, product_data, expected_text):
        svc, mock_client = service
        mock_client.chat.completions.create.return_value = GenericSpecs(summary="test")

        svc.enrich_product(product_data)

        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert user_message["content"] == expected_text

    def test_enrich_product_no_data(self, service):
        svc, _ = service
        result = svc.enrich_product({})
        assert result is None

    def test_enrich_product_api_error(self, service):
        svc, mock_client = service
        mock_client.chat.completions.create.side_effect = APIError("API Fail", request=MagicMock(), body=None)

        result = svc.enrich_product({"description": "test"})
        assert result is None

    def test_enrich_product_timeout_error(self, service):
        svc, mock_client = service
        mock_client.chat.completions.create.side_effect = TimeoutError("Request timed out")

        result = svc.enrich_product({"description": "test"})
        assert result is None

    def test_enrich_product_validation_error(self, service):
        svc, mock_client = service
        mock_client.chat.completions.create.side_effect = ValidationError.from_exception_data(title="test", line_errors=[])

        result = svc.enrich_product({"description": "test"})
        assert result is None

    def test_enrich_product_unexpected_error(self, service):
        svc, mock_client = service
        mock_client.chat.completions.create.side_effect = Exception("Boom")

        result = svc.enrich_product({"description": "test"})
        assert result is None
