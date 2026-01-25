import logging
from decimal import Decimal
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

    def _normalize_price(self, value: Decimal | float | int | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def sync_listing(self, listing: MercadoLibreListing, dry_run: bool = False, force: bool = False) -> bool:
        """
        Synchronizes a single Mercado Libre listing.
        Returns True if the listing was updated, False otherwise.
        """
        base_price = listing.product_master.price
        calculated_price = self._price_engine.calculate(base_price) if base_price is not None else None
        new_price = calculated_price["final_price"] if calculated_price is not None else listing.final_price

        new_quantity = self._stock_engine.get_available_quantity(listing.product_master) if listing.product_master.is_active else 0

        update_payload: dict[str, Any] = {}
        if force:
            normalized_price = self._normalize_price(new_price if new_price is not None else listing.final_price)
            if normalized_price is not None:
                update_payload["price"] = normalized_price
            update_payload["available_quantity"] = new_quantity
        else:
            if new_price is not None and new_price != listing.final_price:
                update_payload["price"] = self._normalize_price(new_price)
            if new_quantity != listing.available_quantity:
                update_payload["available_quantity"] = new_quantity

        if not update_payload:
            logger.debug(f"No changes for listing {listing.ml_id}.")
            return False

        if not listing.ml_id:
            logger.warning(f"Listing {listing.pk} is missing ml_id; skipping remote update.")
            return False

        logger.info(f"Listing {listing.ml_id} requires update. Payload: {update_payload}")

        if not dry_run:
            try:
                self._ml_client.put(f"items/{listing.ml_id}", json=update_payload)
                update_fields = []
                if "price" in update_payload and new_price is not None and calculated_price is not None:
                    listing.final_price = new_price
                    listing.net_price = calculated_price["net_price"]
                    listing.profit = calculated_price["profit"]
                    update_fields.extend(["final_price", "net_price", "profit"])
                if "available_quantity" in update_payload:
                    listing.available_quantity = new_quantity
                    update_fields.append("available_quantity")
                if update_fields:
                    listing.save(update_fields=update_fields)
                logger.info(f"Successfully updated listing {listing.ml_id} on Mercado Libre and database.")
            except Exception as e:
                logger.error(f"Failed to update listing {listing.ml_id}: {e}")
                return False
        return True

    def sync_all_listings(self, dry_run: bool = False, force: bool = False) -> None:
        """
        Synchronizes all active Mercado Libre listings with the local database.
        """
        logger.info("Starting Mercado Libre listings synchronization.")
        updated_count = 0
        no_changes_count = 0

        active_listings = MercadoLibreListing.objects.filter(status=MercadoLibreListing.Status.ACTIVE).select_related("product_master")

        for listing in active_listings:
            if self.sync_listing(listing, dry_run, force):
                updated_count += 1
            else:
                no_changes_count += 1
        logger.info(f"Synchronization finished. Updated: {updated_count}, No changes: {no_changes_count}.")
