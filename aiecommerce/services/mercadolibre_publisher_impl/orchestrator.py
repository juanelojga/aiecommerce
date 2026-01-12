import logging

from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService
from aiecommerce.services.mercadolibre_publisher_impl.selector import ProductSelector

logger = logging.getLogger(__name__)


class PublisherOrchestrator:
    def __init__(self, publisher: MercadoLibrePublisherService):
        self.publisher = publisher

    def run(self, product_code: str, dry_run: bool, sandbox: bool) -> None:
        product = ProductSelector.get_product_by_code(product_code)

        if not product:
            logger.warning(f"Product with code '{product_code}' not found or not marked for Mercado Libre.")
            return

        self.publisher.publish_product(product, dry_run=dry_run, test=sandbox)
