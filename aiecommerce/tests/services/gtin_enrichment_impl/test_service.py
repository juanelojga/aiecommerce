"""Tests for GTINSearchService."""

from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from openai import APIError
from pydantic import ValidationError

from aiecommerce.services.gtin_enrichment_impl.exceptions import ConfigurationError
from aiecommerce.services.gtin_enrichment_impl.schemas import GTINSearchResult
from aiecommerce.services.gtin_enrichment_impl.service import (
    STRATEGY_MODEL_BRAND,
    STRATEGY_NOT_FOUND,
    STRATEGY_RAW_DESCRIPTION,
    STRATEGY_SKU_NAME,
    GTINSearchService,
)


@pytest.fixture
def mock_settings():
    """Mock Django settings for tests."""
    with (
        patch.object(settings, "OPENROUTER_API_KEY", "test-key"),
        patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"),
        patch.object(settings, "GTIN_SEARCH_MODEL", "test-model"),
    ):
        yield settings


@pytest.fixture
def service(mock_settings):
    """Create a GTINSearchService instance with mocked client."""
    with (
        patch("aiecommerce.services.gtin_enrichment_impl.service.OpenAI"),
        patch("aiecommerce.services.gtin_enrichment_impl.service.instructor.from_openai") as mock_instructor,
    ):
        mock_client = MagicMock()
        mock_instructor.return_value = mock_client
        svc = GTINSearchService()
        yield svc, mock_client


class TestGTINSearchServiceInitialization:
    """Tests for service initialization."""

    @patch("aiecommerce.services.gtin_enrichment_impl.service.OpenAI")
    @patch("aiecommerce.services.gtin_enrichment_impl.service.instructor.from_openai")
    def test_initialization_success(self, mock_instructor, mock_openai, mock_settings):
        """Test successful initialization with valid settings."""
        service = GTINSearchService()

        assert service.model_name == "test-model"
        mock_openai.assert_called_once_with(base_url="https://test.url", api_key="test-key")
        mock_instructor.assert_called_once()

    def test_initialization_missing_api_key(self):
        """Test initialization fails when API key is missing."""
        with patch.object(settings, "OPENROUTER_API_KEY", ""):
            with pytest.raises(ConfigurationError) as excinfo:
                GTINSearchService()
            assert "The following settings are required" in str(excinfo.value)

    def test_initialization_missing_base_url(self):
        """Test initialization fails when base URL is missing."""
        with (
            patch.object(settings, "OPENROUTER_API_KEY", "test-key"),
            patch.object(settings, "OPENROUTER_BASE_URL", ""),
        ):
            with pytest.raises(ConfigurationError) as excinfo:
                GTINSearchService()
            assert "The following settings are required" in str(excinfo.value)

    def test_initialization_missing_model(self):
        """Test initialization fails when model is missing."""
        with (
            patch.object(settings, "OPENROUTER_API_KEY", "test-key"),
            patch.object(settings, "OPENROUTER_BASE_URL", "https://test.url"),
            patch.object(settings, "GTIN_SEARCH_MODEL", ""),
        ):
            with pytest.raises(ConfigurationError) as excinfo:
                GTINSearchService()
            assert "The following settings are required" in str(excinfo.value)


class TestGTINValidation:
    """Tests for GTIN validation."""

    def test_validate_gtin_valid_8_digits(self, service):
        """Test validation accepts 8-digit GTIN."""
        svc, _ = service
        assert svc._validate_gtin("12345678") is True

    def test_validate_gtin_valid_12_digits(self, service):
        """Test validation accepts 12-digit GTIN."""
        svc, _ = service
        assert svc._validate_gtin("123456789012") is True

    def test_validate_gtin_valid_13_digits(self, service):
        """Test validation accepts 13-digit GTIN (EAN)."""
        svc, _ = service
        assert svc._validate_gtin("1234567890123") is True

    def test_validate_gtin_valid_14_digits(self, service):
        """Test validation accepts 14-digit GTIN."""
        svc, _ = service
        assert svc._validate_gtin("12345678901234") is True

    def test_validate_gtin_invalid_too_short(self, service):
        """Test validation rejects GTINs shorter than 8 digits."""
        svc, _ = service
        assert svc._validate_gtin("1234567") is False

    def test_validate_gtin_invalid_too_long(self, service):
        """Test validation rejects GTINs longer than 14 digits."""
        svc, _ = service
        assert svc._validate_gtin("123456789012345") is False

    def test_validate_gtin_invalid_non_numeric(self, service):
        """Test validation rejects non-numeric GTINs."""
        svc, _ = service
        assert svc._validate_gtin("12345ABC") is False

    def test_validate_gtin_invalid_empty(self, service):
        """Test validation rejects empty string."""
        svc, _ = service
        assert svc._validate_gtin("") is False

    def test_validate_gtin_invalid_none(self, service):
        """Test validation rejects None."""
        svc, _ = service
        assert svc._validate_gtin(None) is False


class TestSearchWithSKUAndName:
    """Tests for Strategy 1: SKU + Normalized Name."""

    @pytest.mark.django_db
    def test_strategy_success(self, service):
        """Test successful GTIN search using SKU and normalized name."""
        from model_bakery import baker

        svc, mock_client = service

        # Create product with SKU and normalized_name
        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU12345",
            normalized_name="Dell Latitude 5430 Intel Core i5",
        )

        # Mock LLM response
        mock_response = GTINSearchResult(gtin="1234567890123", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("1234567890123", STRATEGY_SKU_NAME)
        mock_client.chat.completions.create.assert_called_once()

        # Verify the query contains SKU and name
        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "SKU12345" in user_message["content"]
        assert "Dell Latitude 5430" in user_message["content"]

    @pytest.mark.django_db
    def test_strategy_skipped_missing_sku(self, service):
        """Test strategy is skipped when SKU is missing."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            normalized_name="Dell Laptop",
        )

        # Mock second strategy to return result
        mock_response = GTINSearchResult(gtin="1234567890123", confidence="medium", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        # Add model_name and brand for second strategy
        product.model_name = "Latitude 5430"
        product.specs = {"Brand": "Dell"}
        product.save()

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("1234567890123", STRATEGY_MODEL_BRAND)

    @pytest.mark.django_db
    def test_strategy_skipped_missing_normalized_name(self, service):
        """Test strategy is skipped when normalized_name is missing."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU12345",
            normalized_name=None,
        )

        # Mock second strategy to return result
        mock_response = GTINSearchResult(gtin="1234567890123", confidence="medium", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        # Add model_name and brand for second strategy
        product.model_name = "Latitude 5430"
        product.specs = {"Brand": "Dell"}
        product.save()

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("1234567890123", STRATEGY_MODEL_BRAND)


class TestSearchWithModelAndBrand:
    """Tests for Strategy 2: Model Name + Brand."""

    @pytest.mark.django_db
    def test_strategy_success_brand_field(self, service):
        """Test successful search using model_name and Brand field."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,  # Skip first strategy
            model_name="Latitude 5430",
            specs={"Brand": "Dell"},
        )

        mock_response = GTINSearchResult(gtin="9876543210987", confidence="high", source="https://dell.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("9876543210987", STRATEGY_MODEL_BRAND)

        # Verify query contains model and brand
        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "Dell" in user_message["content"]
        assert "Latitude 5430" in user_message["content"]

    @pytest.mark.django_db
    def test_strategy_success_lowercase_brand(self, service):
        """Test search works with lowercase 'brand' field."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name="ThinkPad X1",
            specs={"brand": "Lenovo"},  # lowercase
        )

        mock_response = GTINSearchResult(gtin="1111111111111", confidence="medium", source="https://lenovo.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("1111111111111", STRATEGY_MODEL_BRAND)

    @pytest.mark.django_db
    def test_strategy_success_marca_field(self, service):
        """Test search works with 'Marca' field (Spanish)."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name="ProBook 440",
            specs={"Marca": "HP"},  # Spanish
        )

        mock_response = GTINSearchResult(gtin="2222222222222", confidence="high", source="https://hp.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("2222222222222", STRATEGY_MODEL_BRAND)

    @pytest.mark.django_db
    def test_strategy_skipped_missing_model_name(self, service):
        """Test strategy is skipped when model_name is missing."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
            specs={"Brand": "Dell"},
        )

        result = svc.search_gtin(product)

        # All strategies fail
        assert result == (None, STRATEGY_NOT_FOUND)

    @pytest.mark.django_db
    def test_strategy_skipped_missing_brand(self, service):
        """Test strategy is skipped when brand is missing from specs."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name="Latitude 5430",
            specs={},  # No brand
        )

        result = svc.search_gtin(product)

        # All strategies fail
        assert result == (None, STRATEGY_NOT_FOUND)

    @pytest.mark.django_db
    def test_strategy_skipped_null_specs(self, service):
        """Test strategy is skipped when specs is None."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name="Latitude 5430",
            specs=None,
        )

        result = svc.search_gtin(product)

        # All strategies fail
        assert result == (None, STRATEGY_NOT_FOUND)


class TestSearchWithRawDescription:
    """Tests for Strategy 3: Raw Description from ProductDetailScrape."""

    @pytest.mark.django_db
    def test_strategy_success_with_name(self, service):
        """Test successful search using ProductDetailScrape name."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        # Create detail scrape
        baker.make(
            "aiecommerce.ProductDetailScrape",
            product=product,
            name="Dell Latitude 5430 Notebook 14 inch",
            attributes={},
        )

        mock_response = GTINSearchResult(gtin="5555555555555", confidence="low", source="https://shop.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("5555555555555", STRATEGY_RAW_DESCRIPTION)

        # Verify query contains name
        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "Dell Latitude 5430" in user_message["content"]

    @pytest.mark.django_db
    def test_strategy_success_with_attributes(self, service):
        """Test successful search using ProductDetailScrape attributes."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        # Create detail scrape with attributes
        baker.make(
            "aiecommerce.ProductDetailScrape",
            product=product,
            name="HP Laptop",
            attributes={
                "Marca": "HP",
                "Modelo": "ProBook 440 G10",
                "RAM": "16GB",
                "Storage": "512GB SSD",
            },
        )

        mock_response = GTINSearchResult(gtin="6666666666666", confidence="medium", source="https://hp.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("6666666666666", STRATEGY_RAW_DESCRIPTION)

        # Verify query contains attributes
        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "HP Laptop" in user_message["content"]
        assert "Marca: HP" in user_message["content"]

    @pytest.mark.django_db
    def test_strategy_uses_most_recent_scrape(self, service):
        """Test strategy uses the most recent ProductDetailScrape."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        # Create multiple scrapes
        baker.make(
            "aiecommerce.ProductDetailScrape",
            product=product,
            name="Old Product Name",
        )
        baker.make(
            "aiecommerce.ProductDetailScrape",
            product=product,
            name="New Product Name",
        )

        mock_response = GTINSearchResult(gtin="7777777777777", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        assert result == ("7777777777777", STRATEGY_RAW_DESCRIPTION)

        # Verify query uses recent scrape
        _, kwargs = mock_client.chat.completions.create.call_args
        user_message = next(m for m in kwargs["messages"] if m["role"] == "user")
        assert "New Product Name" in user_message["content"]
        assert "Old Product Name" not in user_message["content"]

    @pytest.mark.django_db
    def test_strategy_skipped_no_detail_scrape(self, service):
        """Test strategy is skipped when no ProductDetailScrape exists."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        result = svc.search_gtin(product)

        # All strategies fail
        assert result == (None, STRATEGY_NOT_FOUND)

    @pytest.mark.django_db
    def test_strategy_skipped_empty_scrape_data(self, service):
        """Test strategy is skipped when ProductDetailScrape has no usable data."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        # Create detail scrape with no useful data
        baker.make(
            "aiecommerce.ProductDetailScrape",
            product=product,
            name=None,
            attributes={},
        )

        result = svc.search_gtin(product)

        # All strategies fail
        assert result == (None, STRATEGY_NOT_FOUND)


class TestSearchGTINIntegration:
    """Integration tests for the full search_gtin workflow."""

    @pytest.mark.django_db
    def test_all_strategies_fail_returns_not_found(self, service):
        """Test that NOT_FOUND is returned when all strategies fail."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku=None,
            model_name=None,
        )

        result = svc.search_gtin(product)

        assert result == (None, STRATEGY_NOT_FOUND)

    @pytest.mark.django_db
    def test_invalid_gtin_format_ignored(self, service):
        """Test that invalid GTIN formats are ignored."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
        )

        # Mock returns invalid GTIN (contains letters)
        mock_response = GTINSearchResult(gtin="123ABC789", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        result = svc.search_gtin(product)

        # Should continue to next strategies
        assert result == (None, STRATEGY_NOT_FOUND)

    @pytest.mark.django_db
    def test_null_gtin_from_llm_continues_search(self, service):
        """Test that null GTIN from LLM continues to next strategy."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
            model_name="TestModel",
            specs={"Brand": "TestBrand"},
        )

        # First call returns null, second call returns valid GTIN
        mock_response_1 = GTINSearchResult(gtin=None, confidence="low", source=None)
        mock_response_2 = GTINSearchResult(gtin="8888888888888", confidence="high", source="https://example.com")

        mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("8888888888888", STRATEGY_MODEL_BRAND)
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.django_db
    def test_api_error_continues_to_next_strategy(self, service):
        """Test that API errors in one strategy continue to the next."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
            model_name="TestModel",
            specs={"Brand": "TestBrand"},
        )

        # First call raises APIError, second call succeeds
        mock_response = GTINSearchResult(gtin="9999999999999", confidence="medium", source="https://example.com")
        mock_client.chat.completions.create.side_effect = [
            APIError("API Failed", request=MagicMock(), body=None),
            mock_response,
        ]

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("9999999999999", STRATEGY_MODEL_BRAND)

    @pytest.mark.django_db
    def test_timeout_error_continues_to_next_strategy(self, service):
        """Test that timeout errors in one strategy continue to the next."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
            model_name="TestModel",
            specs={"Brand": "TestBrand"},
        )

        # First call times out, second call succeeds
        mock_response = GTINSearchResult(gtin="1010101010101", confidence="low", source="https://example.com")
        mock_client.chat.completions.create.side_effect = [TimeoutError("Timed out"), mock_response]

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("1010101010101", STRATEGY_MODEL_BRAND)

    @pytest.mark.django_db
    def test_validation_error_continues_to_next_strategy(self, service):
        """Test that validation errors in one strategy continue to the next."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
            model_name="TestModel",
            specs={"Brand": "TestBrand"},
        )

        # First call raises ValidationError, second call succeeds
        mock_response = GTINSearchResult(gtin="1212121212121", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.side_effect = [
            ValidationError.from_exception_data(title="test", line_errors=[]),
            mock_response,
        ]

        result = svc.search_gtin(product)

        # Should succeed with second strategy
        assert result == ("1212121212121", STRATEGY_MODEL_BRAND)


class TestLLMPrompts:
    """Tests for LLM prompt structure."""

    @pytest.mark.django_db
    def test_system_prompt_contains_rules(self, service):
        """Test that system prompt contains important rules."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
        )

        mock_response = GTINSearchResult(gtin="1234567890123", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        svc.search_gtin(product)

        _, kwargs = mock_client.chat.completions.create.call_args
        system_message = next(m for m in kwargs["messages"] if m["role"] == "system")

        # Verify important rules are present
        assert "GTIN" in system_message["content"]
        assert "8-14 digit" in system_message["content"]
        assert "numeric only" in system_message["content"]
        assert "confidence" in system_message["content"]
        assert "source URL" in system_message["content"]

    @pytest.mark.django_db
    def test_extra_headers_present(self, service):
        """Test that extra headers are included in LLM requests."""
        from model_bakery import baker

        svc, mock_client = service

        product = baker.make(
            "aiecommerce.ProductMaster",
            code="PROD001",
            sku="SKU123",
            normalized_name="Test Product",
        )

        mock_response = GTINSearchResult(gtin="1234567890123", confidence="high", source="https://example.com")
        mock_client.chat.completions.create.return_value = mock_response

        svc.search_gtin(product)

        _, kwargs = mock_client.chat.completions.create.call_args

        # Verify extra headers
        assert "extra_headers" in kwargs
        assert "HTTP-Referer" in kwargs["extra_headers"]
        assert "X-Title" in kwargs["extra_headers"]
        assert "AI Ecommerce GTIN Search" in kwargs["extra_headers"]["X-Title"]
