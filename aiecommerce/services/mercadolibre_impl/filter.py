from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from aiecommerce.models.product import ProductMaster


class MercadoLibreFilter:
    def __init__(self):
        self.publication_rules = settings.MERCADOLIBRE_PUBLICATION_RULES
        self.freshness_threshold_hours = settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS

    def _get_freshness_limit(self) -> datetime:
        return timezone.now() - timedelta(hours=self.freshness_threshold_hours)

    def _filter_by_freshness(self, item: ProductMaster) -> bool:
        freshness_limit = self._get_freshness_limit()
        return item.last_updated > freshness_limit

    def is_eligible(self, product: ProductMaster) -> bool:
        # 1. Base Checks:
        if not product.is_active or product.price is None or product.category is None:
            return False

        # 2. Freshness Check:
        if product.last_updated < self._get_freshness_limit():
            return False

        # 3. Category Match:
        for category_key, rules in self.publication_rules.items():
            if category_key.lower() in product.category.lower():
                threshold = rules.get("price_threshold")
                if threshold is not None and product.price >= threshold:
                    return True

        # 4. Default:
        return False

    def get_eligible_products(self) -> QuerySet[ProductMaster]:
        """
        Retrieves products that are eligible for publication based on activity, freshness, and category rules.

        The initial filter is broad, and then each product is checked against the more complex `is_eligible` method.
        """
        freshness_limit = self._get_freshness_limit()
        # Start with a broad filter that can be executed efficiently in the database.
        initial_queryset = ProductMaster.objects.filter(is_active=True, last_updated__gte=freshness_limit)

        # Iterate over the initial queryset and apply the more complex, non-database-optimizable logic.
        eligible_ids = [product.id for product in initial_queryset if self.is_eligible(product)]

        # Return the final, precisely filtered QuerySet.
        return ProductMaster.objects.filter(id__in=eligible_ids)
