from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from model_bakery import baker

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService
from aiecommerce.services.mercadolibre_impl.query_constructor import QueryConstructor
from aiecommerce.services.mercadolibre_impl.selector import ImageCandidateSelector


@pytest.fixture
def mock_service():
    service = MagicMock()
    # Mocking .cse().list().execute()
    service.cse.return_value.list.return_value.execute.return_value = {"items": []}
    return service


def test_dependency_injection(mock_service):
    with patch("aiecommerce.services.mercadolibre_impl.image_search_service.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "key"
        mock_settings.GOOGLE_SEARCH_ENGINE_ID = "id"
        service = ImageSearchService(service=mock_service)
        assert service.api_key == "key"
        assert service.search_engine_id == "id"
        assert service.service == mock_service


def test_subdomain_blocking():
    with patch("aiecommerce.services.mercadolibre_impl.image_search_service.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "k"
        mock_settings.GOOGLE_SEARCH_ENGINE_ID = "i"
        service = ImageSearchService(service=MagicMock())
        service.domain_blocklist = {"amazon.com"}

        assert service._is_blocked("http://amazon.com/img.jpg") is True
        assert service._is_blocked("http://www.amazon.com/img.jpg") is True
        assert service._is_blocked("http://images.amazon.com/img.jpg") is True
        assert service._is_blocked("http://example.com/img.jpg") is False


def test_pagination(mock_service):
    # Mock two pages of results
    page1 = {"items": [{"link": f"http://example.com/img{i}.jpg"} for i in range(10)], "queries": {"nextPage": [{"startIndex": 11}]}}
    page2 = {"items": [{"link": f"http://example.com/img{i}.jpg"} for i in range(11, 16)]}

    mock_service.cse.return_value.list.return_value.execute.side_effect = [page1, page2]

    with patch("aiecommerce.services.mercadolibre_impl.image_search_service.settings") as mock_settings:
        mock_settings.GOOGLE_API_KEY = "k"
        mock_settings.GOOGLE_SEARCH_ENGINE_ID = "i"
        service = ImageSearchService(service=mock_service)
        urls = service.find_image_urls("query", image_search_count=15)

    assert len(urls) == 15
    assert mock_service.cse.return_value.list.call_count == 2
    # Check if first call had num=10, start=1
    args, kwargs = mock_service.cse.return_value.list.call_args_list[0]
    assert kwargs["num"] == 10
    assert kwargs["start"] == 1
    # Check if second call had num=5, start=11
    args, kwargs = mock_service.cse.return_value.list.call_args_list[1]
    assert kwargs["num"] == 5
    assert kwargs["start"] == 11


def test_query_constructor_configuration():
    with patch("aiecommerce.services.mercadolibre_impl.query_constructor.settings") as mock_settings:
        mock_settings.IMAGE_SEARCH_NOISY_TERMS = "NOISY"
        mock_settings.IMAGE_SEARCH_QUERY_SUFFIX = "SUFFIX"

        qc = QueryConstructor()
        assert qc.noisy_terms == "NOISY"
        assert qc.query_suffix == "SUFFIX"


@pytest.mark.django_db
def test_image_candidate_selector_queryset():
    with patch("aiecommerce.services.mercadolibre_impl.filter.settings") as mock_settings:
        mock_settings.MERCADOLIBRE_PUBLICATION_RULES = {"Cat": 100}
        mock_settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS = 24

        selector = ImageCandidateSelector()
        baker.make(ProductMaster, is_active=True, category="Cat", price=150, last_updated=timezone.now())
        baker.make(ProductMaster, is_active=True, category="Cat", price=150, last_updated=timezone.now())

        qs = selector.get_pending_image_products()
        from django.db.models import QuerySet

        assert isinstance(qs, QuerySet)
        assert qs.count() == 2


def test_query_constructor_truncation():
    qc = QueryConstructor(query_suffix="X" * 150)
    product = baker.prepare(ProductMaster, description="desc")
    query = qc.build_query(product)
    assert len(query) == 100
