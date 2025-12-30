from datetime import datetime, timedelta

from django.conf import settings

from aiecommerce.models.product import ProductMaster


class MercadoLibreFilter:
    def __init__(self):
        self.publication_rules = settings.MERCADOLIBRE_PUBLICATION_RULES
        self.freshness_threshold_hours = settings.MERCADOLIBRE_FRESHNESS_THRESHOLD_HOURS

    def _get_freshness_limit(self) -> datetime:
        return datetime.now() - timedelta(hours=self.freshness_threshold_hours)

    def _filter_by_freshness(self, item: ProductMaster) -> bool:
        freshness_limit = self._get_freshness_limit()
        return item.last_updated > freshness_limit
