import logging
import re

from aiecommerce.models import ProductMaster

from .ean_search_client import EANSearchClient
from .google_search_strategy import GoogleGTINStrategy

logger = logging.getLogger(__name__)


def _clean_spec_value(value: str | None) -> str:
    """Removes special characters and extra whitespace from a spec value."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


class GTINDiscoveryOrchestrator:
    """Orchestrates the discovery of GTIN codes for products."""

    def __init__(self, google_strategy: GoogleGTINStrategy, ean_client: EANSearchClient):
        self.google_strategy = google_strategy
        self.ean_client = ean_client

    def _build_tier2_query(self, product: ProductMaster) -> str:
        """Constructs a targeted search query for Tier 2 based on product specs."""
        if product.specs:
            manufacturer = _clean_spec_value(product.specs.get("manufacturer"))
            model_name = _clean_spec_value(product.specs.get("model_name"))
            sku = _clean_spec_value(product.specs.get("sku"))

            # Prioritize a query with all three components if available
            if manufacturer and model_name and sku:
                return f"{manufacturer} {model_name} {sku}"

            # Fallback to a simpler query if some specs are missing
            query_parts = [part for part in [manufacturer, model_name, sku] if part]
            if query_parts:
                return " ".join(query_parts)

        # Ultimate fallback to the product description if specs are unhelpful
        return product.description or ""

    def discover_gtin(self, product: ProductMaster) -> dict[str, str] | None:
        """
        Attempts to discover a GTIN for a given product using a tiered search strategy.

        Tier 1: Google Search Strategy
        - Executes a series of predefined Google searches.

        Tier 2: EAN Search API Fallback
        - Uses a constructed query from specs (manufacturer, model, SKU) to search a barcode database.

        Returns: A dictionary with 'gtin' and 'source' if found, otherwise None.
        """
        # --- TIER 1 ---
        logger.info(f"--- STARTING TIER 1 (GOOGLE) FOR PRODUCT SKU: {product.sku} ---")
        try:
            if result := self.google_strategy.execute(product):
                logger.info(f"--- TIER 1 SUCCESS: Found GTIN for {product.sku} ---")
                return result
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 1 execution: {e}", exc_info=True)
        logger.info(f"--- TIER 1 FAILED FOR: {product.sku} ---")

        # --- TIER 2 ---
        logger.info(f"--- STARTING TIER 2 (EAN SEARCH) FOR PRODUCT SKU: {product.sku} ---")
        try:
            tier2_query = self._build_tier2_query(product)
            if not tier2_query:
                logger.warning(f"Skipping Tier 2 for {product.sku}: No query could be built.")
                return None

            logger.info(f"Tier 2 Search Query: '{tier2_query}'")
            if gtin := self.ean_client.find_gtin(tier2_query):
                logger.info(f"--- TIER 2 SUCCESS: Found GTIN for {product.sku} via EAN Search API. ---")
                return {"gtin": gtin, "source": "ean_search_api"}
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 2 execution: {e}", exc_info=True)

        logger.warning(f"--- ALL TIERS FAILED: Could not discover GTIN for Product SKU: {product.sku} ---")
        return None
