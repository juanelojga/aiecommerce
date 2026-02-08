from django.db.models import Q, QuerySet

from aiecommerce.models import MercadoLibreListing, ProductMaster


class MercadolibreCategorySelector:
    """Encapsulates all filtering logic for MercadoLibre product enrichment."""

    # Configuration constants
    DRY_RUN_LIMIT = 3
    DEFAULT_BATCH_SIZE = 5

    def get_queryset(
        self,
        force: bool,
        dry_run: bool,
        category: str | None = None,
        batch_size: int | None = None,
    ) -> QuerySet[ProductMaster]:
        """
        Builds and returns the queryset of products to be enriched for MercadoLibre.

        Args:
            force: If True, re-processes products that already have active listings.
                   If False, only processes products without listings or with
                   PENDING/ERROR status.
            dry_run: If True, limits the queryset to a small, fixed number for testing.
            category: Optional category filter. If provided, only products in this
                     category will be included.
            batch_size: Number of products to return. Defaults to DEFAULT_BATCH_SIZE
                       if not provided. Ignored when dry_run=True.

        Returns:
            A QuerySet of ProductMaster instances ordered by ID, ready for enrichment.

        Notes:
            Uses select_related to optimize listing status checks and avoid N+1 queries.
        """
        query = ProductMaster.objects.filter(
            is_active=True,
            is_for_mercadolibre=True,
            gtin__isnull=False,
        ).select_related("mercadolibre_listing")

        if category:
            query = query.filter(category=category)

        if dry_run:
            # For a dry run, we fetch a small, predictable sample.
            return query.order_by("id")[: self.DRY_RUN_LIMIT]

        if not force:
            needs_enrichment = Q(mercadolibre_listing__isnull=True) | Q(
                mercadolibre_listing__status__in=[
                    MercadoLibreListing.Status.PENDING,
                    MercadoLibreListing.Status.ERROR,
                ]
            )
            query = query.filter(needs_enrichment)

        # Apply batch size limit
        limit = batch_size if batch_size is not None else self.DEFAULT_BATCH_SIZE
        return query.order_by("id")[:limit]
