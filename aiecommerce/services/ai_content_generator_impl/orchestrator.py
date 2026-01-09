"""
This module defines the AIContentOrchestrator service for coordinating content generation.
"""

import logging
import time
import uuid
from typing import Any, Dict

import instructor

from .description_generator import DescriptionGeneratorService
from .selector import AIContentGeneratorCandidateSelector
from .title_generator import TitleGeneratorService

logger = logging.getLogger(__name__)


class AIContentOrchestrator:
    """Coordinates AI-powered content generation for products."""

    def __init__(
        self,
        title_generator: TitleGeneratorService,
        description_generator: DescriptionGeneratorService,
        client: instructor.Instructor,
        selector: AIContentGeneratorCandidateSelector,
    ):
        """
        Initializes the orchestrator with required generator services.

        Args:
            title_generator: Service for generating product titles.
            description_generator: Service for generating product descriptions.
            client: Optional pre-configured instructor client.
        """
        self.title_generator = title_generator
        self.description_generator = description_generator
        self.client = client
        self.selector = selector

    def run(self, force: bool, dry_run: bool, delay: float = 0.5) -> Dict[str, Any]:
        """
        Generates and updates SEO title and description for a single product.

        Args:
            dry_run: If True, changes are not saved to the database.
            force_refresh: If True, content is regenerated even if it already exists.

        Returns:
            A dictionary containing the processing results, including generated
            content and whether the update was successful.
        """
        queryset = self.selector.get_queryset(force, dry_run)

        total = queryset.count()
        stats = {"total": total, "processed": 0}

        if total == 0:
            logger.info("No products need images enrichment.")
            return stats

        batch_session_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting images enrichment batch {batch_session_id} for {total} products.")

        for product in queryset.iterator(chunk_size=100):
            results: Dict[str, Any] = {"product_id": product.pk, "updated": False, "generated_fields": []}
            should_update = False

            try:
                if force or not product.seo_title:
                    logger.info("Generating SEO title for product %s.", product.pk)
                    product.seo_title = self.title_generator.generate_title(product=product)
                    should_update = True
                    results["generated_fields"].append("seo_title")

                if force or not product.seo_description:
                    logger.info("Generating SEO description for product %s.", product.pk)
                    product.seo_description = self.description_generator.generate_description(product=product)
                    should_update = True
                    results["generated_fields"].append("seo_description")

                if should_update and not dry_run:
                    product.save(update_fields=["seo_title", "seo_description"])
                    results["updated"] = True
                    logger.info("Successfully updated product %s.", product.pk)

            except Exception as e:
                logger.error("Failed to process content for product %s: %s", product.pk, e, exc_info=True)
                results["error"] = str(e)

            stats["processed"] += 1

            if delay > 0:
                time.sleep(delay)

        logger.info(f"Finished content enrichment batch {batch_session_id} for {total} products. Processed {stats['processed']} products.")
        return stats
