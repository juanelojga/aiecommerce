from django.db.models import Q, QuerySet

from aiecommerce.models import ProductMaster


class EnrichmentCandidateSelector:
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
        query = ProductMaster.objects.filter(is_active=True)

        if dry_run:
            # For a dry run, we fetch a small, predictable sample.
            return query.order_by("id")[:3]

        if not force:
            # Standard run: only include products with no specs or missing sku.
            query = query.filter(Q(specs__isnull=True) | Q(specs={}) | Q(sku__isnull=True) | Q(seo_title__isnull=True) | Q(seo_description__isnull=True))

        return query.order_by("id")
