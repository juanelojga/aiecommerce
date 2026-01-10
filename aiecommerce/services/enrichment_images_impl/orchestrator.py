import logging
import time
import uuid

from aiecommerce.services.enrichment_images_impl.selector import EnrichmentImagesCandidateSelector
from aiecommerce.tasks.images import process_product_image

logger = logging.getLogger(__name__)


class EnrichmentImagesOrchestrator:
    """
    Main orchestrator that coordinates both detail scraping and AI enrichment
    for all candidate products.
    """

    def __init__(
        self,
        selector: EnrichmentImagesCandidateSelector,
    ):
        self.selector = selector

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """
        Executes the full enrichment flow (Scrape + AI) for all eligible products.
        Only performs steps if data is missing or if 'force' is True.
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
            if dry_run:
                self.logger_output("--- DRY RUN MODE: No tasks will be enqueued. ---")
                self.logger_output(f"Would process Product ID: {product.id}, SKU: {product.sku}")
                continue

            if product.id:
                try:
                    process_product_image.delay(product.id)
                    self.logger_output(f"Successfully enqueued task for Product ID: {product.id}")
                    stats["processed"] += 1
                except Exception as e:
                    self.logger_output(f"Failed to enqueue task for Product ID: {product.id}. Error: {e}", level="error")

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['processed']} processed")
        return stats

    def logger_output(self, message: str, level: str = "info"):
        if level == "error":
            logger.error(message)
        else:
            logger.info(message)
        print(message)
