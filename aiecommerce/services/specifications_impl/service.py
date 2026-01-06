import logging
from typing import Any

import instructor
from django.conf import settings
from openai import APIError, OpenAI
from pydantic import ValidationError

from .exceptions import ConfigurationError
from .schemas import ProductSpecUnion

logger = logging.getLogger(__name__)


class ProductSpecificationsService:
    def __init__(self) -> None:
        """
        Initializes the service.

        Raises:
            ConfigurationError: If required environment variables are not set.
        """
        # --- Configuration & Validation ---
        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL
        self.model_name = settings.OPENROUTER_CLASSIFICATION_MODEL

        if not all([api_key, base_url, self.model_name]):
            raise ConfigurationError("The following settings are required: OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_CLASSIFICATION_MODEL")

        # Initialize the OpenAI client pointing to OpenRouter
        base_client = OpenAI(base_url=base_url, api_key=api_key)
        # Wrap with Instructor to enable structured output
        self.client: Any = instructor.from_openai(base_client, mode=instructor.Mode.JSON)

    def enrich_product(self, product_data: dict) -> ProductSpecUnion | None:
        """
        Analyzes product data and returns structured specifications.

        Args:
            product_data: A dictionary containing product data to analyze.

        Returns:
            A Pydantic model instance from ProductSpecUnion on success, or None on failure.
        """
        # 1. Prepare the input context with clear labels
        parts = []
        if code := product_data.get("code"):
            parts.append(f"Code: {code}")
        if description := product_data.get("description"):
            parts.append(f"Description: {description}")
        if category := product_data.get("category"):
            parts.append(f"Category: {category}")

        text_to_analyze = "\n".join(parts).strip()

        if not text_to_analyze:
            logger.warning("Product has no text data to analyze. Skipping.")
            return None

        try:
            # 2. Call the LLM with Instructor
            extracted_data: ProductSpecUnion | None = self.client.chat.completions.create(
                model=self.model_name,
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
            logger.error(f"API/Network error for product: {e}", exc_info=True)
            return None
        except ValidationError as e:
            logger.error(f"Validation error for product: Could not parse LLM response. {e}", exc_info=True)
            return None
        except Exception as e:
            logger.critical(f"An unexpected error occurred for product: {e}", exc_info=True)
            return None
