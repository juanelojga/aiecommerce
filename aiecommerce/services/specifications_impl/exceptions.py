class ConfigurationError(Exception):
    """Custom exception for missing service configuration."""

    pass


class EnrichmentError(Exception):
    """Domain error raised for enrichment failures."""

    pass
