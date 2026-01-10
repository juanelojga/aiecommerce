from django.db.models import Q, QuerySet

from aiecommerce.models import ProductMaster


class MercadolibreCategorySelector:
    """Encapsulates all filtering logic for product enrichment."""

    def get_queryset(self, force: bool, dry_run: bool) -> QuerySet[ProductMaster, ProductMaster]:
        """
        Builds and returns the queryset of products to be enriched.

        Args:
            force: If True, re-processes products that already have specs.
            dry_run: If True, limits the queryset to a small, fixed number for testing.

        Returns:
            A QuerySet of ProductMaster instances.
        """
        query = ProductMaster.objects.filter(
            is_active=True,
            is_for_mercadolibre=True,
        )

        if dry_run:
            # For a dry run, we fetch a small, predictable sample.
            return query.order_by("id")[:3]

        if not force:
            needs_enrichment = Q(mercadolibre_listing__isnull=True)
            query = query.filter(needs_enrichment)

        return query.order_by("id")[:2]
