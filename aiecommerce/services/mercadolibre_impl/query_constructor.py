import re
from typing import Optional

from django.conf import settings

from aiecommerce.models.product import ProductMaster


class QueryConstructor:
    """Handles the logic for building search queries from product data."""

    DEFAULT_NOISY_TERMS: str = r"\b(Cop|Si|No|Precio|Stock|Garantia|3yb|W11pro)\b"
    DEFAULT_QUERY_SUFFIX: str = "official product image white background"

    def __init__(
        self,
        noisy_terms: Optional[str] = None,
        query_suffix: Optional[str] = None,
    ):
        # Initialize with defaults
        self.noisy_terms: str = self.DEFAULT_NOISY_TERMS
        self.query_suffix: str = self.DEFAULT_QUERY_SUFFIX

        # Try to get from arguments or settings
        val_noisy = noisy_terms or getattr(settings, "IMAGE_SEARCH_NOISY_TERMS", self.DEFAULT_NOISY_TERMS)
        val_suffix = query_suffix or getattr(settings, "IMAGE_SEARCH_QUERY_SUFFIX", self.DEFAULT_QUERY_SUFFIX)

        # Ensure we have strings (especially if settings are mocked)
        if isinstance(val_noisy, str):
            self.noisy_terms = val_noisy
        if isinstance(val_suffix, str):
            self.query_suffix = val_suffix

    def build_query(self, product: ProductMaster) -> str:
        """Constructs a precise query by prioritizing Brand/Model over raw description."""
        specs = product.specs or {}
        brand = specs.get("brand", "")
        model = specs.get("model", "")
        category = specs.get("category", "")

        if brand and model:
            base_query = f"{brand} {model} {category}"
        else:
            clean_desc = re.sub(self.noisy_terms, "", product.description or "", flags=re.IGNORECASE)
            base_query = " ".join(clean_desc.split()[:6])

        final_query = f"{base_query} {self.query_suffix}"
        cleaned = re.sub(r"[^\w\s]", "", final_query).strip()
        return " ".join(cleaned.split())[:100].strip()
