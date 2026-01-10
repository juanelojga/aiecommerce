from unittest.mock import MagicMock, patch

import pytest
import requests
from django.conf import settings

from aiecommerce.services.tecnomega_product_details_fetcher_impl.detail_fetcher import TecnomegaDetailFetcher


class TestTecnomegaDetailFetcher:
    @pytest.fixture
    def fetcher(self):
        return TecnomegaDetailFetcher()

    @pytest.fixture
    def mock_response(self):
        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        response.text = "<html></html>"
        return response

    def test_init_defaults(self):
        fetcher = TecnomegaDetailFetcher()
        assert isinstance(fetcher.session, requests.Session)
        assert fetcher.base_url == settings.TECNOMEGA_STORE_BASE_URL
        assert fetcher.search_url_template == settings.TECNOMEGA_SEARCH_URL_TEMPLATE

    def test_init_with_session(self):
        custom_session = requests.Session()
        fetcher = TecnomegaDetailFetcher(session=custom_session)
        assert fetcher.session == custom_session

    @patch.object(TecnomegaDetailFetcher, "_fetch_search_results")
    @patch.object(TecnomegaDetailFetcher, "_extract_first_product_url")
    @patch.object(TecnomegaDetailFetcher, "_fetch_product_page")
    def test_fetch_product_detail_html_success(self, mock_fetch_page, mock_extract_url, mock_fetch_search, fetcher):
        mock_fetch_search.return_value = "search_html"
        mock_extract_url.return_value = "http://example.com/product/123"
        mock_fetch_page.return_value = "product_html"

        result = fetcher.fetch_product_detail_html("PROD123")

        assert result == "product_html"
        mock_fetch_search.assert_called_once_with("PROD123")
        mock_extract_url.assert_called_once_with(html="search_html", product_code="PROD123")
        mock_fetch_page.assert_called_once_with("http://example.com/product/123")

    @patch.object(TecnomegaDetailFetcher, "_get")
    def test_fetch_search_results(self, mock_get, fetcher, mock_response):
        mock_response.text = "search result html"
        mock_get.return_value = mock_response

        result = fetcher._fetch_search_results("PROD123")

        expected_url = settings.TECNOMEGA_SEARCH_URL_TEMPLATE.format(product_code="PROD123")
        mock_get.assert_called_once_with(expected_url)
        assert result == "search result html"

    def test_extract_first_product_url_success(self, fetcher):
        html = """
        <div class="flex flex-wrap pt-2">
            <div>
                <a href="/product/some-slug?code=PROD123">
                    <p>Product Name</p>
                </a>
            </div>
        </div>
        """
        url = fetcher._extract_first_product_url(html, "PROD123")
        assert url == f"{settings.TECNOMEGA_STORE_BASE_URL}/product/some-slug?code=PROD123"

    def test_extract_first_product_url_no_grid(self, fetcher):
        html = "<html><body></body></html>"
        with pytest.raises(ValueError, match="Tecnomega product grid not found"):
            fetcher._extract_first_product_url(html, "PROD123")

    def test_extract_first_product_url_no_links(self, fetcher):
        html = '<div class="flex flex-wrap pt-2"></div>'
        with pytest.raises(ValueError, match="No Tecnomega product found for code=PROD123"):
            fetcher._extract_first_product_url(html, "PROD123")

    def test_extract_first_product_url_multiple_links(self, fetcher, caplog):
        html = """
        <div class="flex flex-wrap pt-2">
            <a href="/product/1">Link 1</a>
            <a href="/product/2">Link 2</a>
        </div>
        """
        url = fetcher._extract_first_product_url(html, "PROD123")
        assert url == f"{settings.TECNOMEGA_STORE_BASE_URL}/product/1"
        assert "Multiple Tecnomega results found for code=PROD123; using first" in caplog.text

    @patch.object(TecnomegaDetailFetcher, "_get")
    def test_fetch_product_page(self, mock_get, fetcher, mock_response):
        mock_response.text = "product page html"
        mock_get.return_value = mock_response

        result = fetcher._fetch_product_page("http://example.com/p1")

        mock_get.assert_called_once_with("http://example.com/p1")
        assert result == "product page html"

    def test_get_success(self, fetcher):
        mock_session = MagicMock()
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        fetcher.session = mock_session

        res = fetcher._get("http://test.com")

        assert res == mock_response
        mock_session.get.assert_called_once_with("http://test.com", timeout=15)
        mock_response.raise_for_status.assert_called_once()

    def test_get_failure(self, fetcher):
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        fetcher.session = mock_session

        with pytest.raises(RuntimeError, match="Failed to fetch Tecnomega URL: http://test.com"):
            fetcher._get("http://test.com")
