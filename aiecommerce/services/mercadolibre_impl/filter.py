from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from aiecommerce.models.product import ProductMaster


class MercadoLibreFilter:
    def __init__(
        self,
        publication_rules: Optional[Dict[str, Any]] = None,
        freshness_threshold_hours: Optional[int] = None,
    ):
        self.publication_rules = publication_rules if publication_rules is not None else settings.MERCADOLIBRE_PUBLICATION_RULES
        self.freshness_threshold_hours = (
            freshness_threshold_hours if freshness_threshold_hours is not None else settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS
        )

    def _get_freshness_limit(self, now: Optional[datetime] = None) -> datetime:
        base_time = now or timezone.now()
        return base_time - timedelta(hours=self.freshness_threshold_hours)

    def is_eligible(self, product: ProductMaster, freshness_limit: Optional[datetime] = None) -> bool:
        """
        Evaluates if a single product is eligible based on business rules.
        """
        # 1. Base Checks: Ensure required fields are present and product is active
        if not product.is_active or product.price is None or product.category is None:
            return False

        # 2. Freshness Check:
        limit = freshness_limit or self._get_freshness_limit()
        if product.last_updated is None or product.last_updated < limit:
            return False

        # 3. Rule Evaluation:
        return self._matches_rules(product)

    def _matches_rules(self, product: ProductMaster) -> bool:
        """
        Check if the product matches any of the publication rules.
        Uses exact (case-insensitive) category matching to avoid brittle substring matches.
        """
        if not product.category:
            return False

        product_category = product.category.strip().lower()

        for category_key, rule_config in self.publication_rules.items():
            if category_key.lower() == product_category:
                # Handle both dict-based rules and simple numeric thresholds
                if isinstance(rule_config, dict):
                    threshold = rule_config.get("price_threshold")
                else:
                    threshold = rule_config

                if threshold is not None and product.price >= threshold:
                    return True

        return False

    def get_eligible_products(self) -> QuerySet[ProductMaster]:
        """
        Retrieves products that are eligible for publication.
        Pushes basic filtering to the database and evaluates complex rules in Python.
        """
        now = timezone.now()
        freshness_limit = self._get_freshness_limit(now=now)

        # 1. Database-level filtering: Reduce the number of products to process in memory
        initial_queryset = ProductMaster.objects.filter(
            is_active=True,
            price__isnull=False,
            category__isnull=False,
            last_updated__gte=freshness_limit,
        )

        # 2. Business logic evaluation
        eligible_ids = [product.id for product in initial_queryset if self.is_eligible(product, freshness_limit=freshness_limit)]

        # 3. Return final QuerySet
        return ProductMaster.objects.filter(id__in=eligible_ids)
