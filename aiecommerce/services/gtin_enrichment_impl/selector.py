"""Selector for identifying products that need GTIN enrichment."""

from django.db.models import Q, QuerySet

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
        - Have data for at least one search strategy:
          * Strategy 1: sku AND normalized_name
          * Strategy 2: model_name AND brand in specs
          * Strategy 3: at least one ProductDetailScrape record

        Args:
            limit: Maximum number of products to return (default: 15)

        Returns:
            A QuerySet of ProductMaster instances ordered by last_updated.
        """
        # Strategy requirements:
        # 1. sku_normalized_name: needs both sku and normalized_name
        strategy1_filter = (
            Q(
                sku__isnull=False,
                normalized_name__isnull=False,
            )
            & ~Q(sku="")
            & ~Q(normalized_name="")
        )

        # 2. model_brand: needs model_name and brand in specs (Brand, brand, or Marca)
        strategy2_filter = Q(
            model_name__isnull=False,
            specs__has_any_keys=["Brand", "brand", "Marca"],
        ) & ~Q(model_name="")

        # 3. raw_description: needs at least one ProductDetailScrape
        strategy3_filter = Q(detail_scrapes__isnull=False)

        # Combine strategy filters (product must satisfy at least one)
        has_strategy_data = strategy1_filter | strategy2_filter | strategy3_filter

        query = (
            ProductMaster.objects.filter(
                is_active=True,
                is_for_mercadolibre=True,
                gtin__isnull=True,
            )
            .exclude(gtin_source="NOT_FOUND")
            .filter(has_strategy_data)
            .distinct()  # Avoid duplicates from detail_scrapes join
            .order_by("last_updated")[:limit]
        )

        return query
