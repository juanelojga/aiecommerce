from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from aiecommerce.models import MercadoLibreListing, ProductMaster


class MercadolibreCategorySelector:
    """Encapsulates all filtering logic for MercadoLibre product enrichment."""

    # Configuration constants
    DRY_RUN_LIMIT = 3
    DEFAULT_BATCH_SIZE = 10  # Increased from 3 for better throughput

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
            - Filters products with available stock: stock_principal='Si' AND
              at least one branch has stock='Si' (stock_colon, stock_sur,
              stock_gye_norte, or stock_gye_sur).
            - Uses select_related to optimize listing status checks and avoid N+1 queries.
        """
        query = ProductMaster.objects.filter(
            is_active=True,
            is_for_mercadolibre=True,
            gtin__isnull=False,
        ).select_related("mercadolibre_listing")

        # Filter by stock availability: must have principal stock
        query = query.filter(stock_principal="Si")

        # Define the branch fields to check (must match MercadoLibreStockEngine.BRANCH_FIELDS)
        branch_fields = ["stock_colon", "stock_sur", "stock_gye_norte", "stock_gye_sur"]

        # Build an OR condition: (stock_colon='Si' OR stock_sur='Si' OR ...)
        # This ensures products have inventory in at least one branch
        branch_query = Q()
        for field in branch_fields:
            branch_query |= Q(**{field: "Si"})

        query = query.filter(branch_query)

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

        # Prioritize products without listings over those with PENDING/ERROR status
        # This ensures new products are always processed before re-processing existing listings
        query = query.annotate(
            priority=Case(
                When(mercadolibre_listing__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        # Apply batch size limit
        limit = batch_size if batch_size is not None else self.DEFAULT_BATCH_SIZE
        return query.order_by("priority", "id")[:limit]
