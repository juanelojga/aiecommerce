import logging
from typing import Any, Dict, Optional

import requests

from .exceptions import MLAPIError, MLRateLimitError, MLTokenExpiredError

logger = logging.getLogger(__name__)


class MercadoLibreClient:
    """Resilient client for Mercado Libre API with OAuth2 support."""

    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: Optional[str] = None):
        # Support dynamic injection for Sandbox/Test Users [cite: 56, 60]
        self.access_token = access_token
        self._session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise MLAPIError("No access token provided.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Wrapper for HTTP requests with 401/429 handling[cite: 212, 257]."""
        url = f"{self.BASE_URL}/{path.lstrip('/')}"

        try:
            response = self._session.request(method, url, headers=self._get_headers(), **kwargs)

            if response.status_code == 401:
                # Potential token expiration [cite: 257, 341]
                raise MLTokenExpiredError("Access token expired.")

            if response.status_code == 429:
                # Rate limit hit [cite: 271]
                raise MLRateLimitError("Rate limit exceeded.")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"ML API request failed: {e}")
            raise MLAPIError(f"Request failed: {e}")

    # Helper methods for standard operations
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", path, params=params)

    def post(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", path, json=data)
