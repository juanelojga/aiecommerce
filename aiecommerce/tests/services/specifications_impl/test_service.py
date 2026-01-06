from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from openai import APIError
from pydantic import ValidationError

from aiecommerce.services.specifications_impl.exceptions import ConfigurationError
from aiecommerce.services.specifications_impl.schemas import GenericSpecs
from aiecommerce.services.specifications_impl.service import ProductSpecificationsService


class TestProductSpecificationsService:
    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_initialization_success(self, mock_instructor, mock_openai):
        # Setup settings
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            service = ProductSpecificationsService()

            assert service.model_name == "test-model"
            mock_openai.assert_called_once_with(base_url="https://test.url", api_key="test-key")
            mock_instructor.assert_called_once()

    def test_initialization_failure(self):
        with patch.object(settings, "OPENROUTER_API_KEY", None):
            with pytest.raises(ConfigurationError) as excinfo:
                ProductSpecificationsService()
            assert "The following settings are required" in str(excinfo.value)

    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_enrich_product_success(self, mock_instructor, mock_openai):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client

            expected_specs = GenericSpecs(summary="Test Product")
            mock_client.chat.completions.create.return_value = expected_specs

            service = ProductSpecificationsService()
            product_data = {"code": "PROD1", "description": "A test product", "category": "Test"}

            result = service.enrich_product(product_data)

            assert result == expected_specs
            mock_client.chat.completions.create.assert_called_once()
            args, kwargs = mock_client.chat.completions.create.call_args
            assert kwargs["model"] == "test-model"
            assert "A test product" in kwargs["messages"][1]["content"]

    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_enrich_product_no_data(self, mock_instructor, mock_openai):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client

            service = ProductSpecificationsService()
            result = service.enrich_product({})
            assert result is None

    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_enrich_product_api_error(self, mock_instructor, mock_openai):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client
            mock_client.chat.completions.create.side_effect = APIError("API Fail", request=MagicMock(), body=None)

            service = ProductSpecificationsService()
            result = service.enrich_product({"description": "test"})
            assert result is None

    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_enrich_product_validation_error(self, mock_instructor, mock_openai):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client
            # ValidationError needs at least some arguments for its constructor usually,
            # but we can mock its occurrence.
            mock_client.chat.completions.create.side_effect = ValidationError.from_exception_data(title="test", line_errors=[])

            service = ProductSpecificationsService()
            result = service.enrich_product({"description": "test"})
            assert result is None

    @patch("aiecommerce.services.specifications_impl.service.OpenAI")
    @patch("aiecommerce.services.specifications_impl.service.instructor.from_openai")
    def test_enrich_product_unexpected_error(self, mock_instructor, mock_openai):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"), patch.object(settings, "OPENROUTER_CLASSIFICATION_MODEL", "test-model"):
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Boom")

            service = ProductSpecificationsService()
            result = service.enrich_product({"description": "test"})
            assert result is None
