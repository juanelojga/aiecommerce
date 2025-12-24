import logging
from typing import Optional
from unittest.mock import MagicMock

import pytest
import requests

from aiecommerce.services.scrape_tecnomega_impl.fetcher import HtmlFetcher


class TestCreateSession:
    def test_default_user_agent_and_retry_config(self):
        fetcher = HtmlFetcher()  # no custom UA

        session = fetcher._session

        # User-Agent is set to a non-empty default containing Mozilla
        ua = session.headers.get("User-Agent", "")
        assert ua
        assert "Mozilla/5.0" in ua

        # Adapters mounted for both http and https
        assert "https://" in session.adapters
        assert "http://" in session.adapters

        https_adapter = session.adapters["https://"]
        assert isinstance(https_adapter, requests.adapters.HTTPAdapter)

        retries = https_adapter.max_retries
        # Validate core retry parameters
        assert retries.total == 3
        assert retries.backoff_factor == 1
        # Allowed methods (Retry may store as frozenset or be None)
        assert set(retries.allowed_methods or ()) == {"HEAD", "GET", "OPTIONS"}
        # Status forcelist contains common transient error codes
        assert {429, 500, 502, 503, 504}.issubset(set(retries.status_forcelist))


class TestFetch:
    def test_fetch_success_sets_params_timeout_and_returns_text(self):
        # Prepare a fetcher and stub its session.get
        fetcher = HtmlFetcher(user_agent="UA-Test")

        class FakeResponse:
            text: str
            encoding: Optional[str]

            def __init__(self) -> None:
                self.text = "<html>ok</html>"
                self.encoding = None

            def raise_for_status(self) -> None:
                return None

        fake_resp = FakeResponse()

        session_mock = MagicMock()
        session_mock.get.return_value = fake_resp
        fetcher._session = session_mock

        url = "https://example.com/search"
        category = "laptops"

        result = fetcher.fetch(url, category)

        # Verify the call parameters
        session_mock.get.assert_called_once_with(url, params={"buscar": category}, timeout=60)

        # fetch sets encoding to utf-8 and returns text
        assert fake_resp.encoding == "utf-8"
        assert result == fake_resp.text

    def test_fetch_logs_and_raises_on_request_exception(self, caplog):
        fetcher = HtmlFetcher()
        session_mock = MagicMock()
        session_mock.get.side_effect = requests.RequestException("boom")
        fetcher._session = session_mock

        url = "https://example.com/search"
        category = "boomcat"

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.RequestException):
                fetcher.fetch(url, category)

        # Ensure an error log was written with the URL
        assert any("Failed to fetch content from" in rec.getMessage() and url in rec.getMessage() for rec in caplog.records)

    def test_fetch_logs_info_on_start_and_success(self, caplog):
        fetcher = HtmlFetcher()

        class FakeResponse:
            text: str = "<html>ok</html>"

            def raise_for_status(self) -> None:
                return None

        session_mock = MagicMock()
        session_mock.get.return_value = FakeResponse()
        fetcher._session = session_mock

        url = "https://example.com/search"
        category = "phones"

        with caplog.at_level(logging.INFO):
            fetcher.fetch(url, category)

        # Info logs for start and success
        messages = [rec.getMessage() for rec in caplog.records]
        assert any("Fetching content from" in m and url in m for m in messages)
        assert any("Successfully fetched content from" in m and url in m for m in messages)
