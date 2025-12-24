from dataclasses import dataclass, field
from typing import List

from django.conf import settings

from .exceptions import ScrapeConfigurationError

DEFAULT_CATEGORIES = ["notebook"]


def _parse_categories(value: str) -> List[str]:
    """
    Parses a comma-separated categories env var.
    Falls back to DEFAULT_CATEGORIES when not defined.
    """
    if not value:
        return DEFAULT_CATEGORIES.copy()

    categories = [c.strip() for c in value.split(",") if c.strip()]

    return categories or DEFAULT_CATEGORIES.copy()


@dataclass(frozen=True)
class ScrapeConfig:
    """Encapsulates all configuration for a scraping run."""

    base_url: str = getattr(settings, "TECNOMEGA_STOCK_LIST_BASE_URL", "https://www.tecnomega.com/buscar")

    categories: List[str] = field(default_factory=lambda: _parse_categories(getattr(settings, "TECNOMEGA_SCRAPE_CATEGORIES", "")))

    dry_run: bool = False

    def __post_init__(self):
        if not self.base_url:
            raise ScrapeConfigurationError("Base URL cannot be empty.")
        if not self.categories:
            raise ScrapeConfigurationError("Categories list cannot be empty.")

    def get_base_url(self) -> str:
        """Constructs the full URL for a given category."""
        return self.base_url
