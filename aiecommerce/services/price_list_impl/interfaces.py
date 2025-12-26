import io
from typing import Dict, List, Protocol

import pandas as pd


class UrlResolver(Protocol):
    def resolve(self, base_url: str) -> str: ...


class FileDownloader(Protocol):
    def download(self, url: str) -> io.BytesIO: ...


class CategoryResolver(Protocol):
    def resolve_categories(self, df: pd.DataFrame) -> pd.DataFrame: ...


class PriceListParser(Protocol):
    def parse(self, content: io.BytesIO) -> List[Dict]: ...
