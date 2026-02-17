"""Selector for identifying products that need GTIN enrichment."""

from django.db.models import QuerySet

from aiecommerce.models import ProductMaster


class GTINEnrichmentCandidateSelector:
    """Encapsulates filtering logic for products that need GTIN enrichment."""

    def get_batch(self, limit: int = 15) -> QuerySet[ProductMaster, ProductMaster]:
        """
        Returns a batch of products that need GTIN enrichment.

        Filters for products that:
        - Are active (is_active=True)
        - Are eligible for MercadoLibre (is_for_mercadolibre=True)
        - Don't have a GTIN yet (gtin__isnull=True)
        - Haven't been marked as NOT_FOUND (gtin_source != "NOT_FOUND")

        Args:
            limit: Maximum number of products to return (default: 15)

        Returns:
            A QuerySet of ProductMaster instances ordered by last_updated.
        """
        query = (
            ProductMaster.objects.filter(
                is_active=True,
                is_for_mercadolibre=True,
                gtin__isnull=True,
            )
            .exclude(gtin_source="NOT_FOUND")
            .order_by("last_updated")[:limit]
        )

        return query
