import logging
import time
import uuid

from django.db import transaction

from aiecommerce.models import ProductDetailScrape
from aiecommerce.services.tecnomega_product_details_fetcher_impl.detail_fetcher import TecnomegaDetailFetcher
from aiecommerce.services.tecnomega_product_details_fetcher_impl.detail_parser import TecnomegaDetailParser
from aiecommerce.services.tecnomega_product_details_fetcher_impl.selector import TecnomegaDetailSelector

logger = logging.getLogger(__name__)


class TecnomegaDetailOrchestrator:
    """
    Orchestrates the resolution, fetching, parsing, and persistence of
    deep product tecnomega_product_details_fetcher_impl using a ForeignKey relationship.
    """

    def __init__(self, selector: TecnomegaDetailSelector, fetcher: TecnomegaDetailFetcher, parser: TecnomegaDetailParser):
        """Initialize with selector, fetcher, and parser components.

        Args:
            selector: Selector to find products needing detail enrichment.
            fetcher: Fetcher to retrieve product HTML from Tecnomega.
            parser: Parser to extract product data from HTML.
        """
        self.selector = selector
        self.fetcher = fetcher
        self.parser = parser

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """Execute the full enrichment flow for all eligible products.

        Args:
            force: Whether to re-process products that already have details.
            dry_run: If True, simulate without saving changes.
            delay: Seconds to wait between processing each product.

        Returns:
            Dictionary with total and processed product counts.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "processed": 0}

        if total == 0:
            logger.info("No products need enrichment.")
            return stats

        batch_session_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting enrichment batch {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            if dry_run:
                logger.info("--- DRY RUN MODE: No tasks will be enqueued. ---")
                logger.info(f"Would process Product ID: {product.code}")
                continue

            if product.code:
                try:
                    # 1. Fetch HTML using the distributor code
                    html = self.fetcher.fetch_product_detail_html(product.code)

                    # 2. Parse data
                    data = self.parser.parse(html)
                    attrs = data.get("attributes", {})

                    with transaction.atomic():
                        # 3. Update the SKU on the master record
                        sku = attrs.get("sku")
                        if sku:
                            product.sku = sku
                            product.save(update_fields=["sku"])

                            # 4. Create the detail record linked by ForeignKey
                            ProductDetailScrape.objects.update_or_create(
                                product=product,  # Direct FK assignment
                                name=data.get("name"),
                                price=data.get("price"),
                                currency=data.get("currency", "USD"),
                                attributes=attrs,
                                image_urls=data.get("images", []),
                                raw_html=html,
                                scrape_session_id=batch_session_id,
                            )
                        else:
                            logger.warning(f"No SKU found for product {product.code}. Skipping detail creation.")

                    stats["processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to enqueue task for Product ID: {product.code}. Error: {e}")

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['processed']} processed")
        return stats
