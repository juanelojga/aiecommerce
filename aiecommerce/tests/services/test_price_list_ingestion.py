import io
from typing import Dict, List

import pytest

from aiecommerce.services.price_list_impl.exceptions import IngestionError
from aiecommerce.services.price_list_impl.interfaces import (
    FileDownloader,
    PriceListParser,
    UrlResolver,
)
from aiecommerce.services.price_list_ingestion import PriceListIngestionService


class _Resolver(UrlResolver):
    def __init__(self, result: str | None = None, err: Exception | None = None):
        self.result = result or "https://example.com/file.xlsx"
        self.err = err
        self.calls: List[Dict] = []

    def resolve(self, base_url: str) -> str:  # type: ignore[override]
        self.calls.append({"base_url": base_url})
        if self.err:
            raise self.err
        return self.result


class _Downloader(FileDownloader):
    def __init__(self, content: io.BytesIO | None = None, err: Exception | None = None):
        self.content = content or io.BytesIO(b"dummy")
        self.err = err
        self.calls: List[Dict] = []

    def download(self, url: str) -> io.BytesIO:  # type: ignore[override]
        self.calls.append({"url": url})
        if self.err:
            raise self.err
        return self.content


class _Parser(PriceListParser):
    def __init__(self, data: List[Dict] | None = None, err: Exception | None = None):
        self.data = data or [{"sku": "A1"}, {"sku": "B2"}]
        self.err = err
        self.calls: List[Dict] = []

    def parse(self, content: io.BytesIO) -> List[Dict]:  # type: ignore[override]
        self.calls.append({"content_len": len(content.getvalue())})
        if self.err:
            raise self.err
        return self.data


def test_process_happy_path_calls_dependencies_and_returns_data() -> None:
    resolver = _Resolver(result="https://resolved.example.com/list.xlsx")
    downloader = _Downloader(content=io.BytesIO(b"xlsx-bytes"))
    expected = [{"sku": "X"}, {"sku": "Y"}]
    parser = _Parser(data=expected)

    service = PriceListIngestionService(url_resolver=resolver, downloader=downloader, parser=parser)

    result = service.process(base_url="https://base.example.com")

    assert result == expected
    # Ensure call order by verifying inputs passed between components
    assert resolver.calls == [{"base_url": "https://base.example.com"}]
    assert downloader.calls == [{"url": "https://resolved.example.com/list.xlsx"}]
    # parser saw the same content we provided to downloader
    assert parser.calls == [{"content_len": len(b"xlsx-bytes")}]


@pytest.mark.parametrize(
    "stage",
    [
        "resolver",
        "downloader",
        "parser",
    ],
)
def test_process_returns_empty_list_on_ingestion_error(stage: str) -> None:
    base_url = "https://base.example.com"
    if stage == "resolver":
        resolver = _Resolver(err=IngestionError("fail resolve"))
        downloader = _Downloader()
        parser = _Parser()
    elif stage == "downloader":
        resolver = _Resolver()
        downloader = _Downloader(err=IngestionError("fail download"))
        parser = _Parser()
    else:  # parser
        resolver = _Resolver()
        downloader = _Downloader()
        parser = _Parser(err=IngestionError("fail parse"))

    service = PriceListIngestionService(url_resolver=resolver, downloader=downloader, parser=parser)

    result = service.process(base_url)

    assert result == []

    # Ensure that when an earlier stage fails, later stages aren't called
    if stage == "resolver":
        assert downloader.calls == []
        assert parser.calls == []
    elif stage == "downloader":
        assert downloader.calls != []  # download attempted
        assert parser.calls == []  # parse not attempted
    else:  # parser error still records a call to parser
        assert parser.calls != []
