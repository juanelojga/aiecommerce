import logging

from aiecommerce.services.mercadolibre_publisher_impl.publisher import MercadoLibrePublisherService
from aiecommerce.services.mercadolibre_publisher_impl.selector import ProductSelector

logger = logging.getLogger(__name__)


class PublisherOrchestrator:
    """Orchestrates the publication of a single product to Mercado Libre."""

    def __init__(self, publisher: MercadoLibrePublisherService):
        """Initialize with a publisher service.

        Args:
            publisher: The service to handle Mercado Libre API calls.
        """
        self.publisher = publisher

    def run(self, product_code: str, dry_run: bool, sandbox: bool) -> None:
        """Run the publication process for a single product.

        Args:
            product_code: The unique code of the product to publish.
            dry_run: If True, prepare without sending to API.
            sandbox: If True, use the sandbox environment.
        """
        product = ProductSelector.get_product_by_code(product_code)

        if not product:
            logger.warning(f"Product with code '{product_code}' not found or not marked for Mercado Libre.")
            return

        self.publisher.publish_product(product, dry_run=dry_run, test=sandbox)
