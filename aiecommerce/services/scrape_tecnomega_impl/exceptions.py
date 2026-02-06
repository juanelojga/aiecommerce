"""Tecnomega scraping exceptions.

This module provides Tecnomega scraping specific exceptions that inherit
from the standardized exception hierarchy.

Note:
    All exceptions in this module are deprecated aliases for the standardized
    exceptions. New code should import directly from aiecommerce.services.exceptions.
"""

from aiecommerce.services.exceptions import (
    ScrapeConfigurationError,
)
from aiecommerce.services.exceptions import (
    ScrapingError as ScrapeError,
)

__all__ = [
    "ScrapeConfigurationError",
    "ScrapeError",
]
