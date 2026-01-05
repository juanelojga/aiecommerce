import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TecnomegaDetailFetcher:
    """Handles resilient HTML fetching for single product pages."""

    def __init__(self, user_agent: Optional[str] = None):
        self._session = self._create_session(user_agent)

    def _create_session(self, user_agent: Optional[str]) -> requests.Session:
        """Configures a requests session with retry logic."""
        session = requests.Session()
        session.headers.update({"User-Agent": user_agent or ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")})
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch(self, product_code: str) -> str:
        """
        Fetches the product detail page for a given product code.

        NOTE: The URL structure is a placeholder and needs to be confirmed.
              The current implementation will likely fail.
        """
        # FIXME: Confirm the correct URL structure for Tecnomega product pages.
        # This is a guess and is likely incorrect.
        url = f"https://www.tecnomega.com/producto/{product_code}"
        logger.info(f"Fetching product detail from {url}")
        try:
            response = self._session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch product detail for code {product_code} from {url}: {e}")
            return ""
