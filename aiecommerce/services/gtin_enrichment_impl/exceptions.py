"""Exceptions for GTIN enrichment service."""


class GTINEnrichmentError(Exception):
    """Base exception for GTIN enrichment errors."""

    pass


class ConfigurationError(GTINEnrichmentError):
    """Raised when required settings are missing."""

    pass
