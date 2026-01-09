import logging
import time
import uuid

from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector
from aiecommerce.services.specifications_impl.orchestrator import ProductSpecificationsOrchestrator

logger = logging.getLogger(__name__)


class EnrichmentOrchestrator:
    """
    Main orchestrator that coordinates both detail scraping and AI enrichment
    for all candidate products.
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
        Executes the full enrichment flow (Scrape + AI) for all eligible products.
        Only performs steps if data is missing or if 'force' is True.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "enriched": 0}

        if total == 0:
            logger.info("No products need enrichment.")
            return stats

        batch_session_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting enrichment batch {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            # --- STEP: AI Enrichment ---
            if not force and hasattr(product, "specs") and product.specs:
                self.logger_output(f"Product {product.code}: Skipping enrichment (specs already present)")
                continue

            try:
                enrich_success, _ = self.specs_orchestrator.process_product(product, dry_run)
                if enrich_success:
                    stats["enriched"] += 1
            except Exception as e:
                self.logger_output(f"Product {product.code}: AI enrichment crashed - {e}", level="error")

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['enriched']} processed")
        return stats

    def logger_output(self, message: str, level: str = "info"):
        if level == "error":
            logger.error(message)
        else:
            logger.info(message)
        print(message)
