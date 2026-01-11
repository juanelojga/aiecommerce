from datetime import datetime, timedelta
from typing import Any, Mapping, Optional

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone

from aiecommerce.models.product import ProductMaster


class MercadoLibreFilter:
    def __init__(
        self,
        publication_rules: Optional[Mapping[str, Any]] = None,
        freshness_threshold_hours: Optional[int] = None,
    ) -> None:
        self.publication_rules: Mapping[str, Any] = publication_rules if publication_rules is not None else settings.MERCADOLIBRE_PUBLICATION_RULES
        self.freshness_threshold_hours: int = freshness_threshold_hours if freshness_threshold_hours is not None else settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS

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

                if threshold is not None and product.price is not None and product.price >= threshold:
                    return True

        return False

    def get_eligible_products(self) -> QuerySet[ProductMaster]:
        """
        Retrieves products that are eligible for publication.
        Filters by status, freshness, and business rules directly in the database.
        """
        now = timezone.now()
        freshness_limit = self._get_freshness_limit(now=now)

        # 1. Base QuerySet
        queryset = ProductMaster.objects.filter(
            is_active=True,
            price__isnull=False,
            category__isnull=False,
            last_updated__gte=freshness_limit,
            model_name__isnull=False,
            sku__isnull=False,
            seo_title__isnull=False,
        )

        # 2. Build Q object for publication rules
        rules_q = Q()
        for category_key, rule_config in self.publication_rules.items():
            if isinstance(rule_config, dict):
                threshold = rule_config.get("price_threshold")
            else:
                threshold = rule_config

            if threshold is not None:
                # category__iexact handles case-insensitive matching.
                # strip() is not easily done in pure Q without Trim function,
                # but following the previous logic's intent of exact category match.
                rules_q |= Q(category__iexact=category_key.strip(), price__gte=threshold)

        # 3. Apply rules and return
        if not rules_q:
            return ProductMaster.objects.none()

        return queryset.filter(rules_q)
