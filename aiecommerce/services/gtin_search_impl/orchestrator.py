import logging
import time
import uuid
from typing import Any

from .google_search_strategy import GoogleGTINStrategy
from .selector import GTINSearchSelector

logger = logging.getLogger(__name__)


class GTINDiscoveryOrchestrator:
    """Orchestrates the discovery of GTIN codes for products."""

    def __init__(self, selector: GTINSearchSelector, google_strategy: GoogleGTINStrategy):
        """Initialize with selector and Google search strategy.

        Args:
            selector: Selector to find products needing GTIN discovery.
            google_strategy: Strategy for Google Search GTIN lookup.
        """
        self.selector = selector
        self.google_strategy = google_strategy

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, Any]:
        """Discover GTINs for products using Google Search strategy.

        Args:
            force: Whether to process all products or only those without GTIN.
            dry_run: If True, simulate without saving changes.
            delay: Seconds to wait between processing each product.

        Returns:
            Dictionary with total and processed product counts.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "processed": 0}

        if total == 0:
            logger.info("No products need images enrichment.")
            return stats

        batch_session_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting images enrichment batch {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            logger.info(f"--- STARTING (GOOGLE) FOR PRODUCT SKU: {product.code} ---")
            try:
                result = self.google_strategy.execute(product)
                logger.info(f"--- Found GTIN for {product.code} {result} ---")
                if result and not dry_run:
                    product.gtin = result["gtin"]
                    product.gtin_source = result["gtin_source"]
                    product.save(update_fields=["gtin", "gtin_source"])
            except Exception as e:
                logger.error(f"An unexpected error occurred during execution: {e}", exc_info=True)

            stats["processed"] += 1

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Finished content enrichment batch {batch_session_id} for {total} products. Processed {stats['processed']} products.")
        return stats
