import logging
import time
import uuid

from aiecommerce.services.update_ml_eligibility_impl.selector import UpdateMlEligibilityCandidateSelector

logger = logging.getLogger(__name__)


class UpdateMlEligibilityCandidateOrchestrator:
    """
    Main orchestrator that coordinates the update eligibility flow
    for all candidate products.
    """

    def __init__(
        self,
        selector: UpdateMlEligibilityCandidateSelector,
    ):
        self.selector = selector

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """
        Executes the full update eligibility flow (Scrape + AI) for all eligible products.
        Only performs steps if data is missing or if 'force' is True.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "processed": 0}

        if total == 0:
            logger.info("No products need images update.")
            return stats

        batch_session_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting update ml eligibility {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            if dry_run:
                logger.info("--- DRY RUN MODE: No tasks will be saved. ---")
                logger.info(f"Would process Product ID: {product.code}")
                continue

            product.is_for_mercadolibre = True
            product.save(update_fields=["is_for_mercadolibre"])
            stats["processed"] += 1

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['processed']} processed")
        return stats
