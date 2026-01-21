import logging
from typing import List

from aiecommerce.models import MercadoLibreListing
from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator

logger = logging.getLogger(__name__)


class BatchPublisherOrchestrator:
    def __init__(self, publisher_orchestrator: PublisherOrchestrator):
        self.publisher_orchestrator = publisher_orchestrator

    def _get_pending_listings(self) -> List[MercadoLibreListing]:
        """Fetches all listings with 'PENDING' status and available_quantity > 0 for Mercado Libre."""
        logger.debug("Fetching pending listings for Mercado Libre.")

        # Add condition for available_quantity > 0
        listings = list(
            MercadoLibreListing.objects.filter(
                status=MercadoLibreListing.Status.PENDING,
                available_quantity__gt=0,  # Ensures only listings with stock > 0
            )
        )
        logger.info(f"Found {len(listings)} pending listings for Mercado Libre.")
        return listings

    def run(self, dry_run: bool, sandbox: bool) -> None:
        """
        Processes all pending Mercado Libre listings.

        Args:
            dry_run: If True, prepares and logs the payload without sending.
            sandbox: If True, uses the sandbox environment.
        """
        pending_listings = self._get_pending_listings()

        if not pending_listings:
            logger.info("No pending listings to publish.")
            return

        logger.info(f"Starting batch publication of {len(pending_listings)} listings.")

        for listing in pending_listings:
            if not listing.product_master:
                logger.warning(f"Skipping listing {listing.id} because it has no associated product or product master.")
                continue

            product_code = listing.product_master.code

            if product_code:
                logger.info(f"--- Processing product: {product_code} (Listing ID: {listing.id}) ---")
                try:
                    self.publisher_orchestrator.run(
                        product_code=product_code,
                        dry_run=dry_run,
                        sandbox=sandbox,
                    )
                    logger.info(f"--- Successfully processed product: {product_code} ---")
                except Exception as e:
                    logger.error(f"Failed to process product {product_code}: {e}", exc_info=True)
                    continue
        logger.info("--- Batch publication process finished ---")
