import logging
import time
import uuid

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_category_impl.category_predictor import MercadolibreCategoryPredictorService
from aiecommerce.services.mercadolibre_category_impl.price import MercadoLibrePriceEngine
from aiecommerce.services.mercadolibre_category_impl.selector import MercadolibreCategorySelector

logger = logging.getLogger(__name__)


class MercadolibreEnrichmentCategoryOrchestrator:
    """
    Main orchestrator that coordinates both detail scraping and AI enrichment
    for all candidate products.
    """

    def __init__(self, selector: MercadolibreCategorySelector, category_predictor: MercadolibreCategoryPredictorService, price_engine: MercadoLibrePriceEngine):
        self.selector = selector
        self.category_predictor = category_predictor
        self.price_engine = price_engine

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> dict[str, int]:
        """
        Executes the full enrichment flow (Scrape + AI) for all eligible products.
        Only performs steps if data is missing or if 'force' is True.
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
            try:
                if not product.seo_title:
                    logger.warning(f"Product {product.code} has no SEO title, skipping category prediction.")
                    continue

                category_id = self.category_predictor.predict_category(product.seo_title)
                listing, created = MercadoLibreListing.objects.get_or_create(product_master=product)

                # Calculate prices and update the listing
                if product.price is not None:
                    calculated_prices = self.price_engine.calculate(product.price)
                    listing.final_price = calculated_prices["final_price"]
                    listing.net_price = calculated_prices["net_price"]
                    listing.profit = calculated_prices["profit"]
                else:
                    logger.warning(f"Product {product.code} has no price, skipping price calculation for listing.")

                if not dry_run:
                    listing.category_id = category_id
                    listing.save()
                    logger.info(f"Category ID {category_id} and prices saved for product {product.code}")
                stats["processed"] += 1
            except Exception as e:
                logger.error(f"Product {product.code}: AI enrichment crashed - {e}")

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Batch completed: {stats['processed']} processed")
        return stats
