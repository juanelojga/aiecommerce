from datetime import datetime, timedelta
from typing import Any, Mapping

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone

from aiecommerce.models import ProductMaster


class UpdateMlEligibilityCandidateSelector:
    """Encapsulates all filtering logic for product enrichment."""

    def __init__(self) -> None:
        self.freshness_threshold_hours: int = settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS
        self.publication_rules: Mapping[str, Any] = settings.MERCADOLIBRE_PUBLICATION_RULES

    def _get_freshness_limit(self) -> datetime:
        base_time = timezone.now()
        return base_time - timedelta(hours=self.freshness_threshold_hours)

    def get_queryset(self, force: bool, dry_run: bool) -> QuerySet[ProductMaster, ProductMaster]:
        """
        Builds and returns the queryset of products to be enriched.

        Args:
            force: If True, re-processes products that already have specs.
            dry_run: If True, limits the queryset to a small, fixed number for testing.

        Returns:
            A QuerySet of ProductMaster instances.
        """
        freshness_limit = self._get_freshness_limit()

        query = ProductMaster.objects.filter(
            is_active=True,
            price__isnull=False,
            category__isnull=False,
            last_updated__gte=freshness_limit,
            stock_principal="Si",
        )

        # Define the branch fields to check
        branch_fields = ["stock_colon", "stock_sur", "stock_gye_norte", "stock_gye_sur"]

        # Build an OR condition: (stock_colon='SI' OR stock_sur='SI' OR ...)
        branch_query = Q()
        for field in branch_fields:
            branch_query |= Q(**{field: "Si"})

        query = query.filter(branch_query)

        # 2. Build Q object for publication rules
        publication_rules_query = Q()
        for category_key, rule_config in self.publication_rules.items():
            if isinstance(rule_config, dict):
                threshold = rule_config.get("price_threshold")
            else:
                threshold = rule_config

            if threshold is not None:
                # category__iexact handles case-insensitive matching.
                # strip() is not easily done in pure Q without Trim function,
                # but following the previous logic's intent of exact category match.
                publication_rules_query |= Q(category__iexact=category_key.strip(), price__gte=threshold)

        query = query.filter(publication_rules_query)

        if dry_run:
            # For a dry run, we fetch a small, predictable sample.
            return query.order_by("id")[:3]

        if not force:
            query = query.filter(is_for_mercadolibre=False)

        return query.order_by("id")
