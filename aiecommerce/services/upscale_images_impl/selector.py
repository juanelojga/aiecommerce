from django.db.models import QuerySet

from aiecommerce.models import ProductMaster


class UpscaleHighResSelector:
    """
    Selector for finding ProductMaster candidates for high-resolution image upscaling.
    """

    def get_candidates(self, product_code: str | None = None) -> QuerySet[ProductMaster]:
        """
        Retrieves ProductMaster candidates for image processing.

        Args:
            product_code: If provided, retrieves only the specified product.

        Returns:
            A QuerySet of ProductMaster objects.
        """
        base_query = ProductMaster.objects.filter(is_active=True, price__isnull=False, category__isnull=False, is_for_mercadolibre=True, detail_scrapes__image_urls__isnull=False)

        if product_code:
            return base_query.filter(code=product_code)

        # Returns products that do not have any 'ProductImage' records where 'is_processed' is True.
        return base_query.exclude(images__is_processed=True)
