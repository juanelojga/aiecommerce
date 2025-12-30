import pytest
from model_bakery import baker

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search import ImageSearchService


@pytest.fixture
def image_search_service():
    """Fixture for ImageSearchService instance."""
    return ImageSearchService()


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
    # The expected query will only contain the static suffix
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
