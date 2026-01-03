"""
This module defines the AIContentOrchestrator service for coordinating content generation.
"""

import logging
import os
from typing import Any, Dict, Optional

import instructor
from django.db import models
from openai import OpenAI

from aiecommerce.models import ProductMaster

from .description_generator import DescriptionGeneratorService
from .title_generator import TitleGeneratorService

logger = logging.getLogger(__name__)


class AIContentOrchestrator:
    """Coordinates AI-powered content generation for products."""

    def __init__(
        self,
        title_generator: TitleGeneratorService,
        description_generator: DescriptionGeneratorService,
        client: Optional[instructor.Instructor] = None,
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
        self._client = client

    @property
    def client(self) -> instructor.Instructor:
        """
        Lazily initializes the instructor client if not provided.
        """
        if self._client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            base_url = os.environ.get("OPENROUTER_BASE_URL")

            if not api_key or not base_url:
                # Fallback to default OpenAI if OpenRouter env vars are not set
                # This will raise the OpenAIError if OPENAI_API_KEY is also missing,
                # but only when the client is actually accessed.
                self._client = instructor.from_openai(OpenAI())
            else:
                self._client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))
        return self._client

    def process_product_content(
        self,
        product: ProductMaster,
        dry_run: bool = False,
        force_refresh: bool = False,
        model_name: str = "google/gemini-1.5-flash-001",
    ) -> Dict[str, Any]:
        """
        Generates and updates SEO title and description for a single product.

        Args:
            product: The ProductMaster instance to process.
            dry_run: If True, changes are not saved to the database.
            force_refresh: If True, content is regenerated even if it already exists.
            model_name: The name of the language model to use for generation.

        Returns:
            A dictionary containing the processing results, including generated
            content and whether the update was successful.
        """
        results: Dict[str, Any] = {"product_id": product.pk, "updated": False, "generated_fields": []}
        should_update = False

        try:
            if force_refresh or not product.seo_title:
                logger.info("Generating SEO title for product %s.", product.pk)
                product.seo_title = self.title_generator.generate_title(product=product)
                should_update = True
                results["generated_fields"].append("seo_title")

            if force_refresh or not product.seo_description:
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

        return results

    def process_batch(
        self,
        limit: int = 10,
        dry_run: bool = False,
        force_refresh: bool = False,
        model_name: str = "google/gemini-1.5-flash-001",
    ) -> int:
        """
        Processes a batch of products to generate missing AI content.

        Args:
            limit: The maximum number of products to process.
            dry_run: If True, changes are not saved to the database.
            force_refresh: If True, content is regenerated for all products in the batch.
            model_name: The name of the language model to use.

        Returns:
            The number of products successfully processed.
        """
        logger.info(
            "Starting AI content generation batch. Limit: %d, Dry Run: %s, Force Refresh: %s",
            limit,
            dry_run,
            force_refresh,
        )

        products_to_process = ProductMaster.objects.filter(is_for_mercadolibre=True)

        if not force_refresh:
            products_to_process = products_to_process.filter(models.Q(seo_title__isnull=True) | models.Q(seo_description__isnull=True))

        products_to_process = products_to_process.order_by("?")[:limit]

        processed_count = 0
        for product in products_to_process:
            try:
                result = self.process_product_content(
                    product=product,
                    dry_run=dry_run,
                    force_refresh=force_refresh,
                    model_name=model_name,
                )
                if result.get("updated") or (dry_run and not result.get("error")):
                    processed_count += 1
            except Exception as e:
                logger.error(
                    "Unhandled error in batch processing for product %s: %s",
                    product.pk,
                    e,
                    exc_info=True,
                )

        logger.info("AI content generation batch finished. Processed %d products.", processed_count)
        return processed_count
