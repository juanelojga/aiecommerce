import logging

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadoLibreClosePublicationService:
    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._ml_client = ml_client

    def remove_listing(self, listing: MercadoLibreListing, dry_run: bool = False) -> bool:
        """
        Closes a single Mercado Libre listing and removes it locally.
        Returns True if the listing was closed and deleted, False otherwise.
        """
        if not listing.ml_id:
            logger.warning("Listing %s has no Mercado Libre id; skipping.", listing.pk)
            return False
        if dry_run:
            logger.info("Dry run: would close listing %s.", listing.ml_id)
            return True
        if not dry_run:
            try:
                self._ml_client.put(f"items/{listing.ml_id}", json={"status": "closed"})
                listing.delete()
                logger.info(
                    "Closed listing %s on Mercado Libre and removed it from the database.",
                    listing.ml_id,
                )
            except Exception:
                logger.exception("Failed to close listing %s.", listing.ml_id)
                return False
        return True

    def remove_all_listings(self, dry_run: bool = False) -> None:
        """
        Closes all out-of-stock active Mercado Libre listings and removes them locally.
        """
        logger.info("Starting Mercado Libre listings close operation.")
        updated_count = 0
        failed_count = 0

        listings_to_close = MercadoLibreListing.objects.filter(status=MercadoLibreListing.Status.ACTIVE, available_quantity=0)

        for listing in listings_to_close:
            if self.remove_listing(listing, dry_run):
                updated_count += 1
            else:
                failed_count += 1
        logger.info(
            "Close operation finished. Closed: %s, Failed: %s.",
            updated_count,
            failed_count,
        )
