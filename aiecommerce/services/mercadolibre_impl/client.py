import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLRateLimitError, MLTokenExpiredError

logger = logging.getLogger(__name__)


@dataclass
class MercadoLibreConfig:
    """Configuration for the Mercado Libre API client."""

    client_id: str
    client_secret: str
    base_url: str = "https://api.mercadolibre.com"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0


class MercadoLibreClient:
    """
    Resilient client for Mercado Libre API with OAuth2 support and multiple user contexts.
    """

    def __init__(self, access_token: Optional[str] = None, config: Optional[MercadoLibreConfig] = None):
        """
        Initializes the client. Supports dynamic access_token injection
        to toggle between Real and Test Users.

        Token refresh is handled externally (e.g., by MercadoLibreAuthService).
        """
        self.access_token = access_token
        self.config = config or MercadoLibreConfig(
            client_id=getattr(settings, "MERCADOLIBRE_CLIENT_ID", ""),
            client_secret=getattr(settings, "MERCADOLIBRE_CLIENT_SECRET", ""),
            base_url=getattr(settings, "MERCADOLIBRE_BASE_URL", "https://api.mercadolibre.com"),
        )
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Configures a session with retry logic for rate limits (429) and server errors (5xx)."""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
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

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts sensitive information from dictionaries for logging."""
        sensitive_keys = {"client_id", "client_secret", "access_token", "refresh_token", "code"}
        return {k: ("***" if k in sensitive_keys else v) for k, v in data.items()}

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Validates the response and handles common error codes.
        Raises domain-specific exceptions.
        """
        if response.status_code == 401:
            logger.warning("Mercado Libre access token expired (401).")
            raise MLTokenExpiredError("Token expired. Refresh required.")

        if response.status_code == 429:
            # Although Retry should handle this, we keep it for cases where retries are exhausted
            # or not applicable, but we clarify it in the log.
            logger.error("Mercado Libre rate limit reached (429) after retries.")
            raise MLRateLimitError("Rate limit exceeded.")

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "Unknown"
            error_body = e.response.text if e.response is not None else "No response body"
            logger.error(f"ML API HTTP Error: {status_code} - {error_body}")
            raise MLAPIError(f"HTTP Error {status_code}: {error_body}")

        if response.content:
            try:
                return response.json()
            except ValueError:
                logger.error(f"Failed to parse JSON response: {response.text}")
                return {"raw_body": response.text}
        return {}

    def _send_request(self, method: str, url: str, use_auth: bool = True, **kwargs: Any) -> Dict[str, Any]:
        """Low-level method to send a request and handle common exceptions."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.config.timeout

        if use_auth:
            headers = kwargs.get("headers", {})
            headers.update(self._get_headers())
            kwargs["headers"] = headers

        try:
            response = self._session.request(method, url, **kwargs)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"ML API Network Error: {e}")
            raise MLAPIError(f"Network Error: {e}")

    def _oauth_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dedicated method for OAuth2 token requests."""
        url = f"{self.config.base_url}/oauth/token"
        masked_data = self._mask_sensitive_data(data)
        logger.debug(f"Sending OAuth request with payload: {masked_data}")
        return self._send_request("POST", url, use_auth=False, json=data)

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges an authorization code for an access token and refresh token."""
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        return self._oauth_request(payload)

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token using a refresh token."""
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
        }
        return self._oauth_request(payload)

    def request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Orchestrates API calls. Handles 401s for token lifecycle
        and 429s for rate limiting.
        """
        url = f"{self.config.base_url}/{path.lstrip('/')}"
        return self._send_request(method, url, use_auth=True, **kwargs)

    def get(self, path: str, params: Optional[Dict] = None, **kwargs: Any) -> Dict[str, Any]:
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs: Any) -> Dict[str, Any]:
        return self.request("POST", path, data=data, json=json, **kwargs)

    def put(self, path: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs: Any) -> Dict[str, Any]:
        return self.request("PUT", path, data=data, json=json, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        return self.request("DELETE", path, **kwargs)
