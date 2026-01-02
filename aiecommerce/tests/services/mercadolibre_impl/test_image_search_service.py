from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService


class TestImageSearchService:
    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        # Mocking .cse().list().execute()
        service.cse.return_value.list.return_value.execute.return_value = {"items": []}
        return service

    def test_initialization_with_di(self, mock_service):
        service = ImageSearchService(api_key="test_api_key", search_engine_id="test_cx", service=mock_service)
        assert service.api_key == "test_api_key"
        assert service.search_engine_id == "test_cx"
        assert service.service == mock_service

    def test_initialization_missing_credentials(self):
        with patch("aiecommerce.services.mercadolibre_impl.image_search_service.settings", spec=[]):
            with pytest.raises(ValueError, match="API credentials missing."):
                ImageSearchService(api_key=None, search_engine_id=None)

    def test_is_blocked(self, mock_service):
        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service)
        service.domain_blocklist = {"blocked.com"}

        assert service._is_blocked("https://blocked.com/image.jpg") is True
        assert service._is_blocked("https://sub.blocked.com/image.jpg") is True
        assert service._is_blocked("https://allowed.com/image.jpg") is False
        assert service._is_blocked("") is True

    def test_find_image_urls_pagination(self, mock_service):
        # Mock 12 results (10 on page 1, 2 on page 2)
        page1 = {"items": [{"link": f"https://example.com/{i}.jpg"} for i in range(10)], "queries": {"nextPage": [{"startIndex": 11}]}}
        page2 = {"items": [{"link": f"https://example.com/{i}.jpg"} for i in range(10, 12)]}
        mock_service.cse.return_value.list.return_value.execute.side_effect = [page1, page2]

        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service)
        urls = service.find_image_urls("test query", image_search_count=12)

        assert len(urls) == 12
        assert mock_service.cse.return_value.list.call_count == 2

        # Verify call parameters for second call
        args, kwargs = mock_service.cse.return_value.list.call_args_list[1]
        assert kwargs["start"] == 11
        assert kwargs["num"] == 2

    def test_find_image_urls_filters_blocked(self, mock_service):
        page = {"items": [{"link": "https://blocked.com/1.jpg"}, {"link": "https://allowed.com/2.jpg"}]}
        mock_service.cse.return_value.list.return_value.execute.return_value = page

        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service, domain_blocklist={"blocked.com"})
        urls = service.find_image_urls("query", image_search_count=5)

        assert len(urls) == 1
        assert urls[0] == "https://allowed.com/2.jpg"

    def test_find_image_urls_http_error(self, mock_service, caplog):
        mock_service.cse.return_value.list.return_value.execute.side_effect = HttpError(resp=MagicMock(status=403), content=b"Forbidden")

        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service)
        urls = service.find_image_urls("query")

        assert urls == []
        assert "HTTP error occurred" in caplog.text

    def test_find_image_urls_unexpected_error(self, mock_service, caplog):
        mock_service.cse.return_value.list.return_value.execute.side_effect = Exception("Boom")

        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service)
        urls = service.find_image_urls("query")

        assert urls == []
        assert "An unexpected error occurred" in caplog.text

    def test_build_search_query_delegation(self, mock_service):
        mock_qc = MagicMock()
        mock_qc.build_query.return_value = "delegated query"
        service = ImageSearchService(api_key="k", search_engine_id="i", service=mock_service, query_constructor=mock_qc)

        product = MagicMock(spec=ProductMaster)
        query = service.build_search_query(product)

        assert query == "delegated query"
        mock_qc.build_query.assert_called_once_with(product)
