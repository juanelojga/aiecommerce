from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from requests import RequestException

from aiecommerce.services.scrape_tecnomega_impl.details.detail_fetcher import TecnomegaDetailFetcher


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def fetcher(mock_session):
    return TecnomegaDetailFetcher(session=mock_session)


class TestTecnomegaDetailFetcher:
    def test_fetch_product_detail_html_success(self, fetcher, mock_session):
        product_code = "ABC-123"
        search_html = """
        <div class="flex flex-wrap pt-2">
            <div class="w-full">
                <div class="bg-white">
                    <a href="/product/some-slug?code=ABC-123">
                        <p>Product Name</p>
                    </a>
                </div>
            </div>
        </div>
        """
        detail_html = "<html>Product Detail Page</html>"

        # Mock search response
        mock_search_resp = MagicMock()
        mock_search_resp.text = search_html
        mock_search_resp.raise_for_status.return_value = None

        # Mock detail response
        mock_detail_resp = MagicMock()
        mock_detail_resp.text = detail_html
        mock_detail_resp.raise_for_status.return_value = None

        mock_session.get.side_effect = [mock_search_resp, mock_detail_resp]

        result = fetcher.fetch_product_detail_html(product_code)

        assert result == detail_html
        assert mock_session.get.call_count == 2

        # Verify first call (search)
        expected_search_url = settings.TECNOMEGA_SEARCH_URL_TEMPLATE.format(product_code=product_code)
        mock_session.get.assert_any_call(expected_search_url, timeout=15)

        # Verify second call (detail)
        expected_detail_url = settings.TECNOMEGA_STORE_BASE_URL + "/product/some-slug?code=ABC-123"
        mock_session.get.assert_any_call(expected_detail_url, timeout=15)

    def test_fetch_product_detail_html_no_grid(self, fetcher, mock_session):
        product_code = "ABC-123"
        search_html = "<div>No grid here</div>"

        mock_search_resp = MagicMock()
        mock_search_resp.text = search_html
        mock_session.get.return_value = mock_search_resp

        with pytest.raises(ValueError, match="Tecnomega product grid not found"):
            fetcher.fetch_product_detail_html(product_code)

    def test_fetch_product_detail_html_no_links(self, fetcher, mock_session):
        product_code = "ABC-123"
        search_html = """
        <div class="flex flex-wrap pt-2">
            <div class="w-full">
            </div>
        </div>
        """

        mock_search_resp = MagicMock()
        mock_search_resp.text = search_html
        mock_session.get.return_value = mock_search_resp

        with pytest.raises(ValueError, match=f"No Tecnomega product found for code={product_code}"):
            fetcher.fetch_product_detail_html(product_code)

    def test_fetch_product_detail_html_multiple_links_warning(self, fetcher, mock_session, caplog):
        product_code = "ABC-123"
        search_html = """
        <div class="flex flex-wrap pt-2">
            <a href="/product/1">Link 1</a>
            <a href="/product/2">Link 2</a>
        </div>
        """
        detail_html = "<html>Detail</html>"

        mock_search_resp = MagicMock()
        mock_search_resp.text = search_html
        mock_detail_resp = MagicMock()
        mock_detail_resp.text = detail_html

        mock_session.get.side_effect = [mock_search_resp, mock_detail_resp]

        with caplog.at_level("WARNING"):
            result = fetcher.fetch_product_detail_html(product_code)

        assert result == detail_html
        assert "Multiple Tecnomega results found for code=ABC-123; using first" in caplog.text

    def test_fetch_product_detail_html_no_href(self, fetcher, mock_session):
        product_code = "ABC-123"
        # We need to trick BeautifulSoup to find a link that matches the selector but returns None for get("href")
        # Or just mock the search_html and then patch BeautifulSoup's select result.

        search_html = """
        <div class="flex flex-wrap pt-2">
            <a href="/product/some-path">Valid?</a>
        </div>
        """
        mock_search_resp = MagicMock()
        mock_search_resp.text = search_html
        mock_session.get.return_value = mock_search_resp

        with patch("aiecommerce.services.scrape_tecnomega_impl.details.detail_fetcher.BeautifulSoup") as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup

            mock_grid = MagicMock()
            mock_soup.select_one.return_value = mock_grid

            mock_link = MagicMock()
            mock_link.get.return_value = None  # Force missing href
            mock_grid.select.return_value = [mock_link]

            with pytest.raises(ValueError, match="Product link found without valid href string"):
                fetcher.fetch_product_detail_html(product_code)

    def test_fetch_product_detail_html_network_error(self, fetcher, mock_session):
        product_code = "ABC-123"
        mock_session.get.side_effect = RequestException("Network error")

        with pytest.raises(RuntimeError, match="Failed to fetch Tecnomega URL"):
            fetcher.fetch_product_detail_html(product_code)

    def test_get_raises_runtime_error_on_request_exception(self, fetcher, mock_session):
        mock_session.get.side_effect = RequestException("Boom")

        with pytest.raises(RuntimeError) as excinfo:
            fetcher._get("http://example.com")

        assert "Failed to fetch Tecnomega URL" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, RequestException)
