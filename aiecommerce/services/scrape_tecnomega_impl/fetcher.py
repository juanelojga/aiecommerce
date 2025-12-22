import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HtmlFetcher:
    """Handles resilient HTML fetching with session management and retries."""

    def __init__(self, base_url: str, user_agent: Optional[str] = None):
        if not base_url:
            raise ValueError("Base URL cannot be empty.")
        self.base_url = base_url
        self._session = self._create_session(user_agent)

    def _create_session(self, user_agent: Optional[str]) -> requests.Session:
        """Configures a requests session with retry logic."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

        # Retry strategy for network issues and server-side errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def fetch_html(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Fetches HTML content for a given search category.

        Args:
            params: A dictionary of query parameters for the request.

        Returns:
            The HTML content as a string.

        Raises:
            requests.RequestException: If the request fails after all retries.
        """
        try:
            logger.info(f"Fetching content from {self.base_url} with params: {params}")
            response = self._session.get(self.base_url, params=params, timeout=60)
            response.raise_for_status()
            response.encoding = "utf-8"  # Ensure correct encoding
            logger.info(f"Successfully fetched content for params: {params}")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch content after retries for params {params}: {e}")
            raise
