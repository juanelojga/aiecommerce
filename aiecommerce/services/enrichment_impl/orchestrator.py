import logging
import time

from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector
from aiecommerce.services.specifications_impl.orchestrator import ProductSpecificationsOrchestrator

logger = logging.getLogger(__name__)


class EnrichmentOrchestrator:
    """
    Main orchestrator that coordinates the enrichment process for all candidate products.
    It uses a selector to find candidates and a specifications orchestrator to process each.
    """

    def __init__(
        self,
        selector: EnrichmentCandidateSelector,
        specs_orchestrator: ProductSpecificationsOrchestrator,
    ):
        self.selector = selector
        self.specs_orchestrator = specs_orchestrator

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """
        Executes the enrichment loop for all eligible products.

        Args:
            force: Whether to re-process products that already have specs.
            dry_run: Whether to skip saving data to the database.
            delay: Time in seconds to wait between products to avoid rate limits.

        Returns:
            A dictionary with execution statistics.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()

        stats = {"total": total, "processed": 0, "success": 0}

        if total == 0:
            logger.info("No products found for enrichment.")
            return stats

        logger.info(f"Starting batch enrichment for {total} products.")

        # Iterate through products using chunks for memory efficiency
        for product in queryset.iterator(chunk_size=100):
            # Delegate individual product processing to the specifications orchestrator
            success, _ = self.specs_orchestrator.process_product(product, dry_run)

            stats["processed"] += 1
            if success:
                stats["success"] += 1
                logger.info(f"Product {product.code}: Successfully enriched.")
            else:
                logger.error(f"Product {product.code}: Enrichment failed.")

            if delay > 0:
                time.sleep(delay)

        return stats
