from dataclasses import dataclass, field
from typing import List

from django.conf import settings

from .exceptions import ScrapeConfigurationError

DEFAULT_CATEGORIES = [
    "memoria-ram",
    "procesadores",
    "tarjetas-de-video",
    "case",
    "fuentes-de-poder",
    "tarjetas-madre",
    "almacenamiento",
]


@dataclass(frozen=True)
class ScrapeConfig:
    """Encapsulates all configuration for a scraping run."""

    base_url: str = getattr(settings, "TECNOMEGA_STOCK_LIST_BASE_URL", "https://www.tecnomega.com/buscar")

    categories: List[str] = field(default_factory=lambda: DEFAULT_CATEGORIES)

    dry_run: bool = False

    def __post_init__(self):
        if not self.base_url:
            raise ScrapeConfigurationError("Base URL cannot be empty.")
        if not self.categories:
            raise ScrapeConfigurationError("Categories list cannot be empty.")

    def get_base_url(self) -> str:
        """Constructs the full URL for a given category."""
        return self.base_url
