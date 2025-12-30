from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from model_bakery import baker

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search import ImageSearchService


@pytest.fixture
def mock_google_service():
    """Fixture to mock the Google Custom Search service."""
    with patch("aiecommerce.services.mercadolibre_impl.image_search.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def image_search_service(mock_google_service):
    """Fixture for ImageSearchService instance with mocked Google service."""
    with patch("aiecommerce.services.mercadolibre_impl.image_search.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "fake_api_key"
        mock_settings.GOOGLE_SEARCH_ENGINE_ID = "fake_engine_id"
        service = ImageSearchService()
        service.service = mock_google_service
        return service


@pytest.mark.django_db
def test_build_search_query_with_all_specs(image_search_service):
    """
    Test that the search query is correctly built when all specs (brand, model, category) are present.
    """
    product = baker.make(
        ProductMaster,
        description="Test Product Description",
        specs={"brand": "BrandX", "model": "ModelY", "category": "CategoryZ"},
    )
    expected_query = "BrandX ModelY CategoryZ Test Product Description official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


@pytest.mark.django_db
def test_build_search_query_with_missing_specs_falls_back_to_description(image_search_service):
    """
    Test that the search query falls back to product.description when specs are missing.
    """
    product = baker.make(
        ProductMaster,
        description="Generic Laptop with no specific brand or model",
        specs={},
    )
    expected_query = "Generic Laptop with no specific brand or model official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


@pytest.mark.django_db
def test_build_search_query_with_partial_specs(image_search_service):
    """
    Test that the search query is built correctly with partial specs.
    """
    product = baker.make(
        ProductMaster,
        description="Another Test Product",
        specs={"brand": "PartialBrand", "category": "Electronics"},
    )
    expected_query = "PartialBrand Electronics Another Test Product official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


@pytest.mark.django_db
def test_build_search_query_with_empty_specs_and_description(image_search_service):
    """
    Test that an empty query is returned if neither specs nor description are available.
    """
    product = baker.make(
        ProductMaster,
        description="",
        specs={},
    )
    expected_query = "official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


@pytest.mark.django_db
def test_build_search_query_with_special_characters(image_search_service):
    """
    Test that special characters in specs and description are removed from the query.
    """
    product = baker.make(
        ProductMaster,
        description="Product with !@#$%^&*() special chars.",
        specs={"brand": "Brand-X", "model": "Model/Y", "category": "Category_Z"},
    )
    expected_query = "BrandX ModelY Category_Z Product with  special chars official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


@pytest.mark.django_db
def test_build_search_query_with_numeric_specs(image_search_service):
    """
    Test that numeric values in specs are correctly included and converted to strings.
    """
    product = baker.make(
        ProductMaster,
        description="Numeric Model Product",
        specs={"brand": "Brand123", "model": 456, "category": "Category789"},
    )
    expected_query = "Brand123 456 Category789 Numeric Model Product official product image white background"
    assert image_search_service.build_search_query(product) == expected_query


def test_find_image_urls_happy_path(image_search_service):
    """
    Test that find_image_urls returns a list of unique URLs.
    """
    mock_response = {
        "items": [
            {"link": "http://example.com/image1.jpg"},
            {"link": "http://example.com/image2.jpg"},
            {"link": "http://example.com/image1.jpg"},  # Duplicate
        ]
    }
    image_search_service.service.cse().list().execute.return_value = mock_response

    urls = image_search_service.find_image_urls("test query")

    assert urls == ["http://example.com/image1.jpg", "http://example.com/image2.jpg"]


def test_find_image_urls_respects_count(image_search_service):
    """
    Test that find_image_urls returns up to `count` URLs.
    """
    mock_response = {"items": [{"link": f"http://example.com/image{i}.jpg"} for i in range(10)]}
    image_search_service.service.cse().list().execute.return_value = mock_response

    urls = image_search_service.find_image_urls("test query", count=3)

    assert len(urls) == 3


def test_find_image_urls_filters_blocked_domains(image_search_service):
    """
    Test that find_image_urls filters out URLs from blocked domains.
    """
    mock_response = {
        "items": [
            {"link": "http://example.com/image1.jpg"},
            {"link": "http://pinterest.com/image2.jpg"},  # blocked
            {"link": "http://good-domain.com/image3.jpg"},
        ]
    }
    image_search_service.service.cse().list().execute.return_value = mock_response

    urls = image_search_service.find_image_urls("test query")

    assert urls == ["http://example.com/image1.jpg", "http://good-domain.com/image3.jpg"]


def test_find_image_urls_no_results(image_search_service):
    """
    Test that find_image_urls returns an empty list when there are no results.
    """
    mock_response: dict = {"items": []}
    image_search_service.service.cse().list().execute.return_value = mock_response

    urls = image_search_service.find_image_urls("test query")

    assert urls == []


def test_find_image_urls_http_error(image_search_service, caplog):
    """
    Test that find_image_urls returns an empty list on HttpError.
    """
    image_search_service.service.cse().list().execute.side_effect = HttpError(MagicMock(status=403), b"Forbidden")

    urls = image_search_service.find_image_urls("test query")

    assert urls == []
    assert "HTTP error occurred" in caplog.text


def test_find_image_urls_with_no_links_in_items(image_search_service):
    """Test that items without a 'link' key are handled gracefully."""
    mock_response = {
        "items": [
            {"title": "image without a link"},
            {"link": "http://example.com/image1.jpg"},
        ]
    }
    image_search_service.service.cse().list().execute.return_value = mock_response
    urls = image_search_service.find_image_urls("test query")
    assert urls == ["http://example.com/image1.jpg"]
