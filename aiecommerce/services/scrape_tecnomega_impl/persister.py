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

    def save_bulk(self, products: List[ProductRawWeb]) -> List[ProductRawWeb]:
        """
        Saves a list of ProductRawWeb objects to the database.

        Args:
            products: A list of ProductRawWeb model instances.

        Returns:
            The list of saved product instances.
        """
        item_count = len(products)
        if not products:
            logger.info("No products to persist.")
            return []

        logger.info(f"Persisting {item_count} products in batches of {self.batch_size}.")
        try:
            with transaction.atomic():
                ProductRawWeb.objects.bulk_create(products, batch_size=self.batch_size)
            logger.info(f"Successfully saved {item_count} products to the database.")
            return products
        except Exception as e:
            logger.error(f"Database error during bulk creation: {e}", exc_info=True)
            # Depending on requirements, you might want to re-raise the exception
            # to let the calling use case handle it.
            raise
