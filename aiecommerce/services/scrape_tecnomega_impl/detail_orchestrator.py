import logging
from typing import Optional

from django.db import transaction

from aiecommerce.models import ProductDetailScrape, ProductImage, ProductMaster
from aiecommerce.services.scrape_tecnomega_impl.details.detail_fetcher import TecnomegaDetailFetcher
from aiecommerce.services.scrape_tecnomega_impl.details.detail_parser import TecnomegaDetailParser

logger = logging.getLogger(__name__)


class TecnomegaDetailOrchestrator:
    """
    Orchestrates the resolution, fetching, parsing, and persistence of
    deep product details using a ForeignKey relationship.
    """

    def __init__(self, fetcher: Optional[TecnomegaDetailFetcher] = None, parser: Optional[TecnomegaDetailParser] = None):
        self.fetcher = fetcher or TecnomegaDetailFetcher()
        self.parser = parser or TecnomegaDetailParser()

    def sync_details(self, product: ProductMaster, session_id: str) -> bool:
        """
        Executes the sync:
        1. Fetch HTML using product.code.
        2. Parse structured data.
        3. Update ProductMaster.sku.
        4. Persist to ProductDetailScrape using the product instance as FK.
        """
        if not product.code:
            logger.error(f"Cannot sync details: product {product.id} has no distributor code.")
            return False

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
                    ProductDetailScrape.objects.create(
                        product=product,  # Direct FK assignment
                        name=data.get("name"),
                        price=data.get("price"),
                        currency=data.get("currency", "USD"),
                        attributes=attrs,
                        image_urls=data.get("images", []),
                        raw_html=html,
                        scrape_session_id=session_id,
                    )

                    # 5. Sync images to the ProductImage table
                    self._sync_images(product, data.get("images", []))
                else:
                    logger.warning(f"No SKU found for product {product.code}. Skipping detail creation.")

            return True

        except Exception as e:
            logger.error(f"Sync failed for {product.code}: {e}", exc_info=True)
            return False

    def _sync_images(self, product: ProductMaster, urls: list[str]):
        """Helper to sync images with the ProductMaster instance."""
        existing = set(product.images.values_list("url", flat=True))
        new_objs = [ProductImage(product=product, url=u, order=idx) for idx, u in enumerate(urls) if u not in existing]
        if new_objs:
            ProductImage.objects.bulk_create(new_objs)
