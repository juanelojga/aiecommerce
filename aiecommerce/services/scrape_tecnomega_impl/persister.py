# --- services/scrape_tecnomega_impl/persister.py ---
import logging
from typing import List

from django.db import transaction

from aiecommerce.models.product import ProductRawWeb

logger = logging.getLogger(__name__)


class ProductPersister:
    """Handles the database persistence of scraped products."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    def persist(self, products: List[ProductRawWeb], dry_run: bool = False):
        """
        Saves a list of ProductRawWeb objects to the database.

        If dry_run is True, it prints statistics instead of saving.

        Args:
            products: A list of ProductRawWeb model instances.
            dry_run: If True, no database changes are made.
        """
        item_count = len(products)
        if not products:
            logger.info("No products to persist.")
            return

        if dry_run:
            logger.info(f"[DRY RUN] Would persist {item_count} products.")
            # Display a preview of the first few items
            for product in products[:5]:
                raw_description_preview = (
                    product.raw_description[:50] if product.raw_description else "No description available"
                )
                logger.info(f"[DRY RUN] Preview: {product.distributor_code} - {raw_description_preview}...")
            return

        logger.info(f"Persisting {item_count} products in batches of {self.batch_size}.")
        try:
            with transaction.atomic():
                ProductRawWeb.objects.bulk_create(products, batch_size=self.batch_size)
            logger.info(f"Successfully saved {item_count} products to the database.")
        except Exception as e:
            logger.error(f"Database error during bulk creation: {e}", exc_info=True)
            # Depending on requirements, you might want to re-raise the exception
            # to let the calling use case handle it.
            raise
