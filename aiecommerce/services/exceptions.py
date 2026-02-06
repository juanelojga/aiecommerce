"""Standardized exception hierarchy for aiecommerce services.

This module defines a consistent exception hierarchy across all services,
enabling proper error handling and debugging throughout the application.

Exception Hierarchy:
    ServiceError (base)
        ConfigurationError
        ExternalServiceError
            APIError
                APITokenError
                    APITokenExpiredError
                    APITokenRefreshError
                    APITokenExchangeError
                    APITokenValidationError
                APIRateLimitError
        DomainError
            ValidationError
            NotFoundError
            ScrapingError
                ScrapeConfigurationError
            IngestionError
                UrlResolutionError
                DownloadError
                ParsingError

Usage:
    from aiecommerce.services.exceptions import (
        ServiceError,
        ConfigurationError,
        APIError,
    )

    try:
        some_service.call()
    except ConfigurationError:
        # Handle missing/invalid configuration
        pass
    except APIError:
        # Handle external API failures
        pass
    except ServiceError:
        # Catch-all for any service-related error
        pass
"""

from typing import Any


class ServiceError(Exception):
    """Base exception for all service-related errors.

    All custom exceptions in the aiecommerce services should inherit from this
    class to enable consistent error handling across the application.

    Attributes:
        message: Human-readable error description.
        details: Optional dictionary with additional error context.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize the exception with message and optional details.

        Args:
            message: Human-readable error description.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ConfigurationError(ServiceError):
    """Raised when service configuration is missing or invalid.

    This includes:
    - Missing required environment variables
    - Invalid configuration values
    - Missing service dependencies
    """

    pass


class ExternalServiceError(ServiceError):
    """Base exception for errors from external services/APIs.

    This is the parent class for all exceptions related to external
    service interactions (APIs, third-party services, etc.).
    """

    pass


class APIError(ExternalServiceError):
    """Raised when an external API request fails.

    This is the base class for API-related errors. Specific API error
    types should inherit from this class.

    Attributes:
        status_code: Optional HTTP status code from the API response.
        response_body: Optional raw response body for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API error with optional HTTP status code.

        Args:
            message: Human-readable error description.
            status_code: Optional HTTP status code from the API response.
            response_body: Optional raw response body for debugging.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        """Return string representation including status code if available."""
        base_msg = self.message
        if self.status_code:
            base_msg = f"[HTTP {self.status_code}] {base_msg}"
        if self.details:
            base_msg = f"{base_msg} (details: {self.details})"
        return base_msg


class APIRateLimitError(APIError):
    """Raised when an API rate limit is exceeded (HTTP 429).

    This exception should be used when an external API returns
    a rate limit error, allowing for retry logic with backoff.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize rate limit error with optional retry hint.

        Args:
            message: Human-readable error description.
            retry_after: Optional seconds to wait before retry.
            **kwargs: Additional arguments passed to APIError.
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class APITokenError(APIError):
    """Base exception for API authentication token errors.

    Parent class for all token-related exceptions including
    expiration, refresh failures, and validation errors.
    """

    pass


class APITokenExpiredError(APITokenError):
    """Raised when an API access token has expired (HTTP 401).

    This indicates that the token needs to be refreshed or
    the user needs to re-authenticate.
    """

    def __init__(self, message: str = "Access token has expired", **kwargs: Any) -> None:
        """Initialize token expired error.

        Args:
            message: Human-readable error description.
            **kwargs: Additional arguments passed to APITokenError.
        """
        super().__init__(message, status_code=401, **kwargs)


class APITokenRefreshError(APITokenError):
    """Raised when token refresh operation fails."""

    pass


class APITokenExchangeError(APITokenError):
    """Raised when token exchange (e.g., OAuth code exchange) fails."""

    pass


class APITokenValidationError(APITokenError):
    """Raised when token response validation fails."""

    pass


class DomainError(ServiceError):
    """Base exception for domain/business logic errors.

    Parent class for exceptions related to business rules,
    validation, and domain-specific errors.
    """

    pass


class ValidationError(DomainError):
    """Raised when domain validation fails.

    Use this for business rule violations that aren't related
    to external service calls.
    """

    pass


class NotFoundError(DomainError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
        """Initialize not found error with resource information.

        Args:
            resource_type: Type of resource that was not found.
            resource_id: Identifier of the missing resource.
            details: Optional dictionary with additional error context.
        """
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ScrapingError(DomainError):
    """Base exception for web scraping errors."""

    pass


class ScrapeConfigurationError(ScrapingError, ConfigurationError):
    """Raised when scraping configuration is invalid.

    This inherits from both ScrapingError and ConfigurationError
    to allow catching by either category.
    """

    pass


class IngestionError(DomainError):
    """Base exception for data ingestion errors."""

    pass


class UrlResolutionError(IngestionError):
    """Raised when URL resolution fails during ingestion."""

    pass


class DownloadError(IngestionError):
    """Raised when file download fails during ingestion."""

    pass


class ParsingError(IngestionError):
    """Raised when data parsing fails during ingestion."""

    pass


class EnrichmentError(DomainError):
    """Raised when content enrichment fails.

    This includes AI content generation, image enrichment,
    and other enhancement operations.
    """

    pass
