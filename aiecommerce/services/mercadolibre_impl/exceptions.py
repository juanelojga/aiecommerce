"""Mercado Libre API exceptions.

This module provides Mercado Libre specific exceptions that inherit
from the standardized exception hierarchy.

Note:
    All exceptions in this module are deprecated aliases for the standardized
    exceptions. New code should import directly from aiecommerce.services.exceptions.
"""

from aiecommerce.services.exceptions import (
    APIError as MLAPIError,
)
from aiecommerce.services.exceptions import (
    APIRateLimitError as MLRateLimitError,
)
from aiecommerce.services.exceptions import (
    APITokenError as MLTokenError,
)
from aiecommerce.services.exceptions import (
    APITokenExchangeError as MLTokenExchangeError,
)
from aiecommerce.services.exceptions import (
    APITokenExpiredError as MLTokenExpiredError,
)
from aiecommerce.services.exceptions import (
    APITokenRefreshError as MLTokenRefreshError,
)
from aiecommerce.services.exceptions import (
    APITokenValidationError as MLTokenValidationError,
)

__all__ = [
    "MLAPIError",
    "MLRateLimitError",
    "MLTokenError",
    "MLTokenExchangeError",
    "MLTokenExpiredError",
    "MLTokenRefreshError",
    "MLTokenValidationError",
]
