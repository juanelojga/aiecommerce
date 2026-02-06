import logging

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadoLibrePausePublicationService:
    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._ml_client = ml_client

    def pause_listing(self, listing: MercadoLibreListing, dry_run: bool = False) -> bool:
        """
        Pauses a single Mercado Libre listing and updates its status locally.
        Returns True if the listing was paused, False otherwise.
        """
        if not listing.ml_id:
            logger.warning("Listing %s has no Mercado Libre id; skipping.", listing.pk)
            return False
        if dry_run:
            logger.info("Dry run: would pause listing %s.", listing.ml_id)
            return True
        try:
            self._ml_client.put(f"items/{listing.ml_id}", json={"status": "paused"})
            listing.status = MercadoLibreListing.Status.PAUSED
            listing.save(update_fields=["status"])
            logger.info(
                "Paused listing %s on Mercado Libre and updated its status locally.",
                listing.ml_id,
            )
        except Exception:
            logger.exception("Failed to pause listing %s.", listing.ml_id)
            return False
        return True

    def pause_all_listings(self, dry_run: bool = False) -> None:
        """
        Pauses all out-of-stock active Mercado Libre listings and updates their status locally.
        """
        logger.info("Starting Mercado Libre listings pause operation.")
        updated_count = 0
        failed_count = 0

        listings_to_pause = MercadoLibreListing.objects.filter(status=MercadoLibreListing.Status.ACTIVE, available_quantity=0)

        for listing in listings_to_pause:
            if self.pause_listing(listing, dry_run):
                updated_count += 1
            else:
                failed_count += 1
        logger.info(
            "Pause operation finished. Paused: %s, Failed: %s.",
            updated_count,
            failed_count,
        )
