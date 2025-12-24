import logging
import os
from typing import Optional, cast

import instructor
from instructor.client import Instructor
from openai import APIError, OpenAI
from pydantic import ValidationError

from aiecommerce.models import ProductMaster

from .exceptions import ConfigurationError
from .schemas import ProductSpecUnion

logger = logging.getLogger(__name__)


class ProductEnrichmentService:
    def __init__(self, client: Optional[Instructor] = None):
        """
        Initializes the service.

        Args:
            client: An optional `instructor.Instructor` client instance.
                    If not provided, a default client is created.

        Raises:
            ConfigurationError: If required environment variables are not set.
        """
        if client:
            self.client = client
        else:
            # --- Configuration & Validation ---
            api_key = os.environ.get("OPENROUTER_API_KEY")
            base_url = os.environ.get("OPENROUTER_BASE_URL")
            self.model_name = os.environ.get("OPENROUTER_CLASSIFICATION_MODEL")

            if not all([api_key, base_url, self.model_name]):
                raise ConfigurationError(
                    "The following environment variables are required: "
                    "OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_CLASSIFICATION_MODEL"
                )

            # Initialize the OpenAI client pointing to OpenRouter
            base_client = OpenAI(base_url=base_url, api_key=api_key)
            # Wrap with Instructor to enable structured output
            self.client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)

    def enrich_product_specs(self, product: ProductMaster) -> ProductSpecUnion | None:
        """
        Analyzes product data and returns structured specifications.

        Args:
            product: The ProductMaster instance to analyze.

        Returns:
            A Pydantic model instance from ProductSpecUnion on success, or None on failure.
        """
        # 1. Prepare the input context with clear labels
        parts = [
            f"Code: {product.code}" if product.code else "",
            f"Description: {product.description}" if product.description else "",
            f"Category: {product.category}" if product.category else "",
        ]
        text_to_analyze = "\n".join(filter(None, parts)).strip()

        if not text_to_analyze:
            logger.warning(f"Product {product.id} has no text data to analyze. Skipping.")
            return None

        try:
            # 2. Call the LLM with Instructor
            extracted_data = self.client.chat.completions.create(
                model=cast(str, self.model_name),  # Ensure mypy knows model_name is a string
                response_model=ProductSpecUnion,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert technical product cataloguer. "
                            "Analyze the product text and extract technical specifications into the correct category structure. "
                            "Select the most appropriate schema from the list provided. "
                            "If specific details are missing, leave them as null."
                        ),
                    },
                    {"role": "user", "content": text_to_analyze},
                ],
                extra_headers={
                    "HTTP-Referer": "https://localhost:8000",
                    "X-Title": "AI Ecommerce Enrichment",
                },
            )
            return extracted_data  # Return the Pydantic model directly

        except (APIError, TimeoutError) as e:
            logger.error(f"API/Network error for product {product.id}: {e}", exc_info=True)
            return None
        except ValidationError as e:
            logger.error(f"Validation error for product {product.id}: Could not parse LLM response. {e}", exc_info=True)
            return None
        except Exception as e:
            logger.critical(f"An unexpected error occurred for product {product.id}: {e}", exc_info=True)
            return None
