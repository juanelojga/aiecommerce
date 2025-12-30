from django.db.models import Q, QuerySet

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.filter import MercadoLibreFilter


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
        base_products = self.ml_filter.get_eligible_products()
        return base_products.filter(Q(image_url__isnull=True) | Q(image_url=""))
