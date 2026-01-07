import logging

from aiecommerce.models import ProductMaster

from .ean_search_client import EANSearchClient
from .google_search_strategy import GoogleGTINStrategy

logger = logging.getLogger(__name__)


class GTINDiscoveryOrchestrator:
    """Orchestrates the discovery of GTIN codes for products."""

    def __init__(self, google_strategy: GoogleGTINStrategy, ean_client: EANSearchClient):
        self.google_strategy = google_strategy
        self.ean_client = ean_client

    def discover_gtin(self, product: ProductMaster) -> dict[str, str] | None:
        """
        Attempts to discover a GTIN for a given product using a tiered search strategy.

        Tier 1: Google Search Strategy
        - Executes a series of predefined Google searches.

        Tier 2: EAN Search API Fallback
        - Uses product.description to search via an external API if Tier 1 fails.

        Returns: A dictionary with 'gtin' and 'source' if found, otherwise None.
        """
        # Tier 1: Google Search Strategy
        logger.info(f"Starting Tier 1 GTIN discovery for Product SKU: {product.sku}")
        try:
            if result := self.google_strategy.execute(product):
                logger.info(f"Tier 1 Success: Found GTIN for {product.sku}")
                return result
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 1 execution: {e}", exc_info=True)

        # Tier 2: External API Fallback
        logger.info(f"Tier 1 failed for {product.sku}. Proceeding to Tier 2 (EAN Search).")
        try:
            if product.description and (gtin := self.ean_client.find_gtin(product.description)):
                logger.info(f"Tier 2 Success: Found GTIN for {product.sku} via EAN Search API.")
                return {"gtin": gtin, "source": "ean_search_api"}
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tier 2 execution: {e}", exc_info=True)

        logger.warning(f"Failed to discover GTIN for Product SKU: {product.sku} after all tiers.")
        return None
