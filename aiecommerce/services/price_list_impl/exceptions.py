"""Price list ingestion exceptions.

This module provides price list specific exceptions that inherit
from the standardized exception hierarchy.

Note:
    All exceptions in this module are deprecated aliases for the standardized
    exceptions. New code should import directly from aiecommerce.services.exceptions.
"""

from aiecommerce.services.exceptions import (
    DownloadError,
    IngestionError,
    UrlResolutionError,
)
from aiecommerce.services.exceptions import (
    ParsingError as IngestionParsingError,
)

# Keep alias for backward compatibility
ParsingError = IngestionParsingError

__all__ = [
    "IngestionError",
    "UrlResolutionError",
    "DownloadError",
    "ParsingError",
]
