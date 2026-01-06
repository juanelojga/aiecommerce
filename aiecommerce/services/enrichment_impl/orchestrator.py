import logging
import time
import uuid

from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector
from aiecommerce.services.scrape_tecnomega_impl.detail_orchestrator import TecnomegaDetailOrchestrator
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
        detail_orchestrator: TecnomegaDetailOrchestrator,
    ):
        self.selector = selector
        self.specs_orchestrator = specs_orchestrator
        self.detail_orchestrator = detail_orchestrator

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """
        Executes the full enrichment flow (Scrape + AI) for all eligible products.
        Only performs steps if data is missing or if 'force' is True.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "processed": 0, "scraped": 0, "enriched": 0}

        if total == 0:
            logger.info("No products need enrichment.")
            return stats

        batch_session_id = f"enrich-batch-{uuid.uuid4().hex[:8]}"
        logger.info(f"Starting enrichment batch {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            stats["processed"] += 1
            desc_preview = (product.description or "No description")[:50]
            logger.info(f"[{stats['processed']}/{total}] Processing: {product.code} - {desc_preview}...")

            # --- STEP 1: Deep Detail Scraping ---
            # Condition: Only run if the product has no SKU or force is True
            if force or not product.sku:
                try:
                    scrape_success = self.detail_orchestrator.sync_details(product, batch_session_id)
                    if scrape_success:
                        stats["scraped"] += 1
                    else:
                        logger.warning(f"Product {product.id}: Deep scraping returned False (no SKU found).")
                except Exception as e:
                    logger.error(f"Product {product.id}: Scraper crashed - {e}", exc_info=True)
            else:
                logger.info(f"Product {product.id}: Skipping scraping (SKU already present: {product.sku}).")

            # --- STEP 2: AI Enrichment ---
            # Condition: Only run if the product has no specs or force is True
            # Note: product.specs defaults to an empty dict {} if not set
            if force or not product.specs:
                try:
                    enrich_success, _ = self.specs_orchestrator.process_product(product, dry_run)
                    if enrich_success:
                        stats["enriched"] += 1
                except Exception as e:
                    logger.error(f"Product {product.id}: AI enrichment crashed - {e}", exc_info=True)
            else:
                logger.info(f"Product {product.id}: Skipping enrichment (Specs already present).")

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['scraped']} scraped, {stats['enriched']} enriched.")
        return stats
