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
def test_build_search_query_prioritizes_specs(image_search_service):
    """
    Test that 'brand', 'model', and 'category' from specs are prioritized.
    """
    product = baker.make(
        ProductMaster,
        specs={"brand": "Apple", "model": "iPhone 14 Pro", "category": "Smartphone"},
        description="This should be ignored.",
    )
    expected = "Apple iPhone 14 Pro Smartphone official product image white background"
    assert image_search_service.build_search_query(product) == expected


@pytest.mark.django_db
def test_build_search_query_falls_back_to_description(image_search_service):
    """
    Test that the description is used when brand and model are missing from specs.
    """
    product = baker.make(
        ProductMaster,
        specs={"category": "Laptop"},
        description="A powerful new laptop from a generic brand",
    )
    expected = "A powerful new laptop from a official product image white background"
    assert image_search_service.build_search_query(product) == expected


@pytest.mark.django_db
def test_build_search_query_filters_noisy_terms_from_description(image_search_service):
    """
    Test that noisy terms are filtered out from the description-based query.
    """
    product = baker.make(
        ProductMaster,
        description="Si, this is a product. No, it is not a toy. Cop it now for a good precio.",
        specs={},
    )
    # "Si", "No", "Cop", "precio" should be removed. It should take the first 6 meaningful words.
    expected = "this is a product official product image white background"
    assert image_search_service.build_search_query(product) == expected


@pytest.mark.django_db
def test_build_search_query_truncates_long_queries(image_search_service):
    """
    Test that the generated query is truncated to 100 characters.
    """
    long_description = "word " * 60
    product = baker.make(
        ProductMaster,
        specs={"brand": "Long", "model": "Query"},
        description=long_description,
    )
    # The spec-based query should be created and then truncated.
    query = image_search_service.build_search_query(product)
    assert len(query) <= 100

    # Test truncation with description fallback
    product_desc = baker.make(
        ProductMaster,
        specs={},
        description=long_description,
    )
    query_desc = image_search_service.build_search_query(product_desc)
    assert len(query_desc) <= 100


@pytest.mark.django_db
def test_build_search_query_handles_empty_product(image_search_service):
    """
    Test that a query with only hero keywords is returned for a product with no specs or description.
    """
    product = baker.make(ProductMaster, specs={}, description="")
    assert image_search_service.build_search_query(product) == "official product image white background"


@pytest.mark.django_db
def test_build_search_query_handles_missing_model(image_search_service):
    """
    Test that description is used if 'model' is missing, even if 'brand' is present.
    """
    product = baker.make(
        ProductMaster,
        specs={"brand": "Sony", "category": "Audio"},
        description="Wireless noise-cancelling headphones",
    )
    # The words from description will be used.
    query = image_search_service.build_search_query(product)
    assert "Sony" not in query
    assert "Wireless" in query
    assert "noisecancelling" in query  # The hyphen is removed by the cleaning regex


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
