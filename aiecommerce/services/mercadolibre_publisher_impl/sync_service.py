import logging
from typing import Any

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_category_impl.price import MercadoLibrePriceEngine
from aiecommerce.services.mercadolibre_category_impl.stock import MercadoLibreStockEngine
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadoLibreSyncService:
    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._ml_client = ml_client
        self._price_engine = MercadoLibrePriceEngine()
        self._stock_engine = MercadoLibreStockEngine()

    def sync_all_listings(self, dry_run: bool = False) -> None:
        """
        Synchronizes all active Mercado Libre listings with the local database.
        """
        logger.info("Starting Mercado Libre listings synchronization.")
        updated_count = 0
        no_changes_count = 0

        active_listings = MercadoLibreListing.objects.filter(status=MercadoLibreListing.Status.ACTIVE).select_related("product_master")

        for listing in active_listings:
            calculated_price = self._price_engine.calculate(listing.product_master.price) if listing.product_master.price else None
            new_price = calculated_price["final_price"] if calculated_price else listing.final_price
            new_quantity = self._stock_engine.get_available_quantity(listing.product_master)

            update_payload: dict[str, Any] = {}
            if new_price != listing.final_price:
                update_payload["price"] = new_price
            if new_quantity != listing.available_quantity:
                update_payload["available_quantity"] = new_quantity

            if not update_payload:
                no_changes_count += 1
                logger.debug(f"No changes for listing {listing.ml_id}.")
                continue

            logger.info(f"Listing {listing.ml_id} requires update. Payload: {update_payload}")
            updated_count += 1

            if not dry_run and listing.ml_id:
                try:
                    self._ml_client.put(f"items/{listing.ml_id}", json=update_payload)
                    if "price" in update_payload and calculated_price:
                        listing.final_price = new_price
                        listing.net_price = calculated_price["net_price"]
                        listing.profit = calculated_price["profit"]
                    if "available_quantity" in update_payload:
                        listing.available_quantity = new_quantity
                    listing.save(update_fields=["final_price", "net_price", "profit", "available_quantity"])
                    logger.info(f"Successfully updated listing {listing.ml_id} on Mercado Libre and database.")
                except Exception as e:
                    logger.error(f"Failed to update listing {listing.ml_id}: {e}")

        logger.info(f"Synchronization finished. Updated: {updated_count}, No changes: {no_changes_count}.")
