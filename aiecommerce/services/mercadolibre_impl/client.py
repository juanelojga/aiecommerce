import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLRateLimitError, MLTokenExpiredError

logger = logging.getLogger(__name__)


class MercadoLibreClient:
    """
    Resilient client for Mercado Libre API with OAuth2 support and multiple user contexts.
    """

    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: Optional[str] = None):
        """
        Initializes the client. Supports dynamic access_token injection
        to toggle between Real and Test Users.
        """
        self.access_token = access_token
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Configures a session with retry logic for rate limits (429) and server errors (5xx)."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        return session

    def _get_headers(self) -> Dict[str, str]:
        """Ensures the Authorization header is sent in every request."""
        if not self.access_token:
            raise MLAPIError("No access token provided. Client must be initialized with a token for this operation.")
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def _oauth_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dedicated method for OAuth2 token requests, which have different auth and error handling."""
        url = f"{self.BASE_URL}/oauth/token"
        try:
            response = self._session.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(f"ML OAuth Error: {e.response.status_code} - {e.response.text}")
            raise MLAPIError(f"OAuth HTTP Error: {e.response.text}")
        except requests.RequestException as e:
            logger.error(f"ML OAuth Network Error: {e}")
            raise MLAPIError(f"OAuth Network Error: {e}")

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges an authorization code for an access token and refresh token."""
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.MERCADOLIBRE_CLIENT_ID,
            "client_secret": settings.MERCADOLIBRE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        return self._oauth_request(payload)

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token using a refresh token."""
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.MERCADOLIBRE_CLIENT_ID,
            "client_secret": settings.MERCADOLIBRE_CLIENT_SECRET,
            "refresh_token": refresh_token,
        }
        return self._oauth_request(payload)

    def request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Orchestrates API calls. Handles 401s for token lifecycle
        and 429s for rate limiting.
        """
        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        headers = self._get_headers()

        try:
            response = self._session.request(method, url, headers=headers, timeout=30, **kwargs)

            if response.status_code == 401:
                logger.warning("Mercado Libre access token expired (401).")
                raise MLTokenExpiredError("Token expired. Refresh required.")

            if response.status_code == 429:
                logger.error("Mercado Libre rate limit reached (429).")
                raise MLRateLimitError("Rate limit exceeded.")

            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.HTTPError as e:
            logger.error(f"ML API HTTP Error: {e.response.text}")
            raise MLAPIError(f"HTTP Error: {e}")
        except requests.RequestException as e:
            logger.error(f"ML API Network Error: {e}")
            raise MLAPIError(f"Network Error: {e}")

    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", path, params=params)

    def post(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", path, json=data)

    def put(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("PUT", path, json=data)
