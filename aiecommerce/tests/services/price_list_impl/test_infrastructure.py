import io
from typing import Any

import pytest
import requests

from aiecommerce.services.price_list_impl.exceptions import DownloadError, UrlResolutionError
from aiecommerce.services.price_list_impl.infrastructure import (
    RequestsFileDownloader,
    TecnomegaUrlResolver,
)


class _FakeResponse:
    def __init__(self, *, content: bytes = b"", url: str = "", ok: bool = True) -> None:
        self.content = content
        self.url = url
        self._ok = ok

    def raise_for_status(self) -> None:  # mimic requests.Response
        if not self._ok:
            raise requests.RequestException("error")


def test_requests_file_downloader_success(monkeypatch: Any) -> None:
    payload = b"hello world"

    def _fake_get(url: str, timeout: int) -> _FakeResponse:  # type: ignore[override]
        assert url == "https://example.com/file.xls"
        assert timeout == 30
        return _FakeResponse(content=payload)

    monkeypatch.setattr(requests, "get", _fake_get)

    downloader = RequestsFileDownloader()
    buf = downloader.download("https://example.com/file.xls")
    assert isinstance(buf, io.BytesIO)
    assert buf.getvalue() == payload


def test_requests_file_downloader_error(monkeypatch: Any) -> None:
    def _fail_get(url: str, timeout: int) -> None:  # type: ignore[override]
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "get", _fail_get)

    downloader = RequestsFileDownloader()
    with pytest.raises(DownloadError):
        downloader.download("https://example.com/file.xls")


def test_tecnomega_url_resolver_success_pdf_to_xls(monkeypatch: Any) -> None:
    def _fake_get(url: str, stream: bool, timeout: int) -> _FakeResponse:  # type: ignore[override]
        assert url == "https://example.com/prices"
        assert stream is True
        assert timeout == 15
        # final URL ends with mixed-case .PDF; should be rewritten to .xls
        return _FakeResponse(url="https://cdn.example.com/path/price-list.PDF")

    monkeypatch.setattr(requests, "get", _fake_get)

    resolver = TecnomegaUrlResolver()
    resolved = resolver.resolve("https://example.com/prices")
    assert resolved == "https://cdn.example.com/path/price-list.xls"


def test_tecnomega_url_resolver_error(monkeypatch: Any) -> None:
    def _fail_get(url: str, stream: bool, timeout: int) -> None:  # type: ignore[override]
        raise requests.RequestException("timeout")

    monkeypatch.setattr(requests, "get", _fail_get)

    resolver = TecnomegaUrlResolver()
    with pytest.raises(UrlResolutionError):
        resolver.resolve("https://example.com/prices")


def test_tecnomega_url_resolver_when_already_xls(monkeypatch: Any) -> None:
    def _fake_get(url: str, stream: bool, timeout: int) -> _FakeResponse:  # type: ignore[override]
        return _FakeResponse(url="https://cdn.example.com/path/price-list.xls")

    monkeypatch.setattr(requests, "get", _fake_get)

    resolver = TecnomegaUrlResolver()
    assert resolver.resolve("https://example.com/prices") == "https://cdn.example.com/path/price-list.xls"
