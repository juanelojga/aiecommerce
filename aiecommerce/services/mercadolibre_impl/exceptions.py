class MLAPIError(Exception):
    """Base exception for Mercado Libre API errors."""

    pass


class MLTokenExpiredError(MLAPIError):
    """Raised when the access token is expired and needs refreshing."""

    pass


class MLInvalidGrantError(MLAPIError):
    """Raised when the refresh token is also invalid (requires re-authorization)[cite: 268]."""

    pass


class MLRateLimitError(MLAPIError):
    """Raised when the API returns a 429 status code[cite: 271]."""

    pass
