import logging

from django.db import transaction

from aiecommerce.models import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator

logger = logging.getLogger(__name__)


class BatchPublisherOrchestrator:
    def __init__(self, publisher_orchestrator: PublisherOrchestrator):
        """Initialize with a publisher orchestrator.

        Args:
            publisher_orchestrator: The orchestrator to handle individual publications.
        """
        self.publisher_orchestrator = publisher_orchestrator

    def _get_pending_listings(self, max_count: int | None = None):
        """Fetch all listings with PENDING status and available stock.

        Args:
            max_count: Maximum number of listings to fetch (optional).

        Returns:
            QuerySet of MercadoLibreListing objects ready for publication.
        """
        logger.debug("Fetching pending listings for Mercado Libre.")

        queryset = (
            MercadoLibreListing.objects.filter(
                status=MercadoLibreListing.Status.PENDING,
                available_quantity__gt=0,  # Ensures only listings with stock > 0
            ).select_related("product_master")  # Prevent N+1 queries
        )

        if max_count:
            queryset = queryset[:max_count]

        count = queryset.count()
        logger.info(f"Found {count} pending listings for Mercado Libre.")
        return queryset

    def run(self, dry_run: bool, sandbox: bool, max_batch_size: int = 100) -> dict:
        """
        Processes all pending Mercado Libre listings.

        Args:
            dry_run: If True, prepares and logs the payload without sending.
            sandbox: If True, uses the sandbox environment.
            max_batch_size: Maximum number of listings to process in one run.

        Returns:
            dict: Statistics with 'success', 'errors', 'skipped' counts.
        """
        pending_listings = self._get_pending_listings(max_count=max_batch_size)
        stats = {"success": 0, "errors": 0, "skipped": 0}

        if not pending_listings:
            logger.info("No pending listings to publish.")
            return stats

        count = pending_listings.count()
        logger.info(f"Starting batch publication of {count} listings.")

        for listing in pending_listings:
            if not listing.product_master:
                logger.warning(f"Skipping listing {listing.id} because it has no associated product or product master.")
                stats["skipped"] += 1
                continue

            product_code = listing.product_master.code

            if product_code:
                logger.info(f"--- Processing product: {product_code} (Listing ID: {listing.id}) ---")
                try:
                    with transaction.atomic():
                        self.publisher_orchestrator.run(
                            product_code=product_code,
                            dry_run=dry_run,
                            sandbox=sandbox,
                        )
                    logger.info(f"--- Successfully processed product: {product_code} ---")
                    stats["success"] += 1
                except Exception as e:
                    logger.error(f"Failed to process product {product_code}: {e}", exc_info=True)
                    stats["errors"] += 1
                    continue

        logger.info(f"--- Batch publication finished: {stats['success']} succeeded, {stats['errors']} failed, {stats['skipped']} skipped ---")
        return stats
