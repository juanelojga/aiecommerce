import logging

from django.db.models import QuerySet

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter

logger = logging.getLogger(__name__)


class ImageCandidateSelector:
    """
    Selects products that are eligible for image searching.
    """

    def __init__(self, ml_filter: MercadoLibreFilter | None = None):
        self.ml_filter = ml_filter or MercadoLibreFilter()

    def get_pending_image_products(self) -> QuerySet[ProductMaster]:
        """
        Returns products that are eligible for MercadoLibre but are missing an image.
        """
        logger.debug("Getting eligible products for image search.")
        base_products = self.ml_filter.get_eligible_products()

        logger.debug("Filtering for products with no images.")
        image_pending_products = base_products.filter(images__isnull=True)

        count = image_pending_products.count()
        logger.info(f"Found {count} products pending image search.")

        return image_pending_products
