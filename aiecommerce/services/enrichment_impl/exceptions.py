"""Product enrichment exceptions.

This module provides enrichment specific exceptions that inherit
from the standardized exception hierarchy.

Note:
    All exceptions in this module are deprecated aliases for the standardized
    exceptions. New code should import directly from aiecommerce.services.exceptions.
"""

from aiecommerce.services.exceptions import ConfigurationError, EnrichmentError

__all__ = [
    "ConfigurationError",
    "EnrichmentError",
]
