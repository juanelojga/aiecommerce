class MLAPIError(Exception):
    """Base exception for all Mercado Libre API-related errors."""

    pass


class MLRateLimitError(MLAPIError):
    """Raised when the API rate limit is exceeded (HTTP 429)."""

    pass


class MLTokenExpiredError(MLAPIError):
    """Raised when the access token is expired (HTTP 401)."""

    pass


class MLTokenError(MLAPIError):
    """Custom exception for token-related errors during OAuth flows."""

    pass
