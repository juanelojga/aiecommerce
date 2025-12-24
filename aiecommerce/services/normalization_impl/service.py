import logging
from typing import Optional, Set

from django.db import transaction
from django.utils import timezone

from aiecommerce.models import ProductMaster, ProductRawPDF, ProductRawWeb
from aiecommerce.services.enrichment_impl import ProductEnrichmentService

from .matcher import FuzzyMatcher

logger = logging.getLogger(__name__)


class ProductNormalizationService:
    """
    Service to normalize product data from scraped web data and PDF price lists
    into a unified ProductMaster record.
    """

    def __init__(self, matcher: Optional[FuzzyMatcher] = None, enrichment_service: Optional[ProductEnrichmentService] = None):
        self.matcher = matcher or FuzzyMatcher()

    @transaction.atomic
    def normalize_products(self, scrape_session_id: Optional[str] = None):
        """
        Main orchestration method to perform the normalization.

        Args:
            scrape_session_id: The specific session to process. If None, the most
                               recent session is used.
        """
        logger.info("Starting product normalization process...")

        # 1. Determine Session
        if not scrape_session_id:
            latest_web_product = ProductRawWeb.objects.order_by("-created_at").first()
            if not latest_web_product:
                logger.warning("No ProductRawWeb entries found. Aborting normalization.")
                return
            scrape_session_id = latest_web_product.scrape_session_id
            logger.info(f"No session ID provided. Using most recent: {scrape_session_id}")
        else:
            logger.info(f"Using provided session ID: {scrape_session_id}")

        # 2. Fetch Data
        web_items = list(ProductRawWeb.objects.filter(scrape_session_id=scrape_session_id))
        pdf_items = list(ProductRawPDF.objects.all())

        if not web_items:
            logger.warning(f"No web items found for session {scrape_session_id}. Aborting.")
            return

        processed_codes: Set[str] = set()
        update_count = 0
        create_count = 0

        # 3. Process & Match
        for web_item in web_items:
            if not web_item.distributor_code:
                continue

            # Find best match in PDF data based on description
            pdf_match = self.matcher.find_best_match(web_item.raw_description, pdf_items)

            # Update or create the ProductMaster record
            product_master, created = ProductMaster.objects.update_or_create(
                code=web_item.distributor_code,
                defaults={
                    "description": web_item.raw_description,
                    "stock_principal": web_item.stock_principal,
                    "stock_colon": web_item.stock_colon,
                    "stock_sur": web_item.stock_sur,
                    "stock_gye_norte": web_item.stock_gye_norte,
                    "stock_gye_sur": web_item.stock_gye_sur,
                    "image_url": web_item.image_url,
                    "price": pdf_match.distributor_price if pdf_match else None,
                    "category": pdf_match.category_header if pdf_match else None,
                    "is_active": True,
                    "last_updated": timezone.now(),
                },
            )

            if created:
                create_count += 1
            else:
                update_count += 1

            processed_codes.add(web_item.distributor_code)

        logger.info(f"Processed {len(web_items)} web items. Created: {create_count}, Updated: {update_count}.")

        # 4. Handle Disappearances
        inactive_count = ProductMaster.objects.exclude(code__in=processed_codes).update(is_active=False)
        logger.info(f"Marked {inactive_count} products as inactive.")

        return {
            "processed_count": len(web_items),
            "created_count": create_count,
            "updated_count": update_count,
            "inactive_count": inactive_count,
        }
