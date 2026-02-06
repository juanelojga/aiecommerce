"""AI Ecommerce services module.

This module provides business logic services for the AI Ecommerce application.
"""

from aiecommerce.services.exceptions import (
    APIError,
    APIRateLimitError,
    APITokenError,
    APITokenExchangeError,
    APITokenExpiredError,
    APITokenRefreshError,
    APITokenValidationError,
    ConfigurationError,
    DomainError,
    DownloadError,
    EnrichmentError,
    ExternalServiceError,
    IngestionError,
    NotFoundError,
    ParsingError,
    ScrapeConfigurationError,
    ScrapingError,
    ServiceError,
    UrlResolutionError,
    ValidationError,
)

__all__ = [
    # Base exceptions
    "ServiceError",
    "ConfigurationError",
    "ExternalServiceError",
    "DomainError",
    # API exceptions
    "APIError",
    "APIRateLimitError",
    "APITokenError",
    "APITokenExpiredError",
    "APITokenRefreshError",
    "APITokenExchangeError",
    "APITokenValidationError",
    # Domain exceptions
    "ValidationError",
    "NotFoundError",
    "ScrapingError",
    "ScrapeConfigurationError",
    "IngestionError",
    "UrlResolutionError",
    "DownloadError",
    "ParsingError",
    "EnrichmentError",
]
