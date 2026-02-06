import logging
from datetime import timedelta

from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadoLibreClosePublicationService:
    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._ml_client = ml_client

    def close_listing(self, listing: MercadoLibreListing, dry_run: bool = False) -> bool:
        """
        Closes a single Mercado Libre listing on ML and removes it from the database.
        Returns True if the listing was closed, False otherwise.
        """
        if not listing.ml_id:
            logger.warning("Listing %s has no Mercado Libre id; skipping.", listing.pk)
            return False
        if dry_run:
            logger.info("Dry run: would close listing %s.", listing.ml_id)
            return True
        try:
            self._ml_client.put(f"items/{listing.ml_id}", json={"status": "closed"})
            listing_id = listing.ml_id
            listing.delete()
            logger.info(
                "Closed listing %s on Mercado Libre and removed from database.",
                listing_id,
            )
        except Exception:
            logger.exception("Failed to close listing %s.", listing.ml_id)
            return False
        return True

    def close_all_paused_listings(self, hours: int = 48, dry_run: bool = False) -> None:
        """
        Closes all Mercado Libre listings that have been paused for the specified hours
        and removes them from the database.
        """
        logger.info("Starting Mercado Libre listings close operation.")
        updated_count = 0
        failed_count = 0

        cutoff_time = timezone.now() - timedelta(hours=hours)
        listings_to_close = MercadoLibreListing.objects.filter(
            status=MercadoLibreListing.Status.PAUSED,
            updated_at__lte=cutoff_time,
        )

        for listing in listings_to_close:
            if self.close_listing(listing, dry_run):
                updated_count += 1
            else:
                failed_count += 1
        logger.info(
            "Close operation finished. Closed: %s, Failed: %s.",
            updated_count,
            failed_count,
        )
