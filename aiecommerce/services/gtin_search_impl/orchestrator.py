import logging

from aiecommerce.models import ProductMaster

from .ean_api_strategy import EANSearchAPIStrategy
from .google_search_strategy import GoogleGTINStrategy

logger = logging.getLogger(__name__)


class GTINDiscoveryOrchestrator:
    """Orchestrates the discovery of GTIN codes for products."""

    def __init__(self, ean_api_strategy: EANSearchAPIStrategy, google_strategy: GoogleGTINStrategy):
        self.ean_api_strategy = ean_api_strategy
        self.google_strategy = google_strategy

    def discover_gtin(self, product: ProductMaster) -> dict[str, str] | None:
        """
        Attempts to discover a GTIN for a given product using a tiered search strategy.

        Tier 1: EAN Search API Strategy
        - High-priority search against a barcode database.

        Tier 2: Google Search Strategy
        - Fallback that executes a series of predefined Google searches.

        Returns: A dictionary with 'gtin' and 'source' if found, otherwise None.
        """
        # --- TIER 1 ---
        logger.info(f"--- STARTING TIER 1 (EAN API) FOR PRODUCT SKU: {product.sku} ---")
        try:
            if gtin := self.ean_api_strategy.search_for_gtin(product):
                logger.info(f"--- TIER 1 SUCCESS: Found GTIN for {product.sku} ---")
                return {"gtin": gtin, "source": "EAN_API"}
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 1 execution: {e}", exc_info=True)
        logger.info(f"--- TIER 1 FAILED FOR: {product.sku} ---")

        # --- TIER 2 ---
        logger.info(f"--- STARTING TIER 2 (GOOGLE) FOR PRODUCT SKU: {product.sku} ---")
        try:
            if result := self.google_strategy.execute(product):
                logger.info(f"--- TIER 2 SUCCESS: Found GTIN for {product.sku} ---")
                return result
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 2 execution: {e}", exc_info=True)
        logger.info(f"--- TIER 2 FAILED FOR: {product.sku} ---")

        logger.warning(f"--- ALL TIERS FAILED: Could not discover GTIN for Product SKU: {product.sku} ---")
        return None
