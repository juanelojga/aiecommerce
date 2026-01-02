from typing import Any, Optional

from aiecommerce.models.product import ProductMaster


class ImageCandidateSelector:
    """
    A service to select product candidates for image processing.
    """

    def find_products_without_images(self, limit: Optional[int] = None) -> Any:
        """
        Finds products that are active, destined for Mercado Libre, and have no associated images.

        Returns:
            A QuerySet of ProductMaster instances.
        """
        qs = ProductMaster.objects.filter(
            is_active=True,
            is_for_mercadolibre=True,
            images__isnull=True,
        ).distinct()
        if limit:
            qs = qs[:limit]
        return qs
