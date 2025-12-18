import io
import re

import requests
from requests import RequestException

from aiecommerce.services.price_list_impl.exceptions import (
    DownloadError,
    UrlResolutionError,
)
from aiecommerce.services.price_list_impl.interfaces import (
    FileDownloader,
    UrlResolver,
)


class RequestsFileDownloader(FileDownloader):
    def download(self, url: str) -> io.BytesIO:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return io.BytesIO(response.content)
        except RequestException as e:
            raise DownloadError(f"Failed to download file from {url}") from e


class TecnomegaUrlResolver(UrlResolver):
    def resolve(self, base_url: str) -> str:
        try:
            response = requests.get(base_url, stream=True, timeout=15)
            response.raise_for_status()
            final_url = response.url
            return re.sub(r"\.pdf", ".xls", final_url, flags=re.IGNORECASE)
        except RequestException as e:
            raise UrlResolutionError(f"Failed to resolve download URL from {base_url}") from e
