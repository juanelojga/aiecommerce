"""Product specifications exceptions.

This module provides specifications specific exceptions that inherit
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
