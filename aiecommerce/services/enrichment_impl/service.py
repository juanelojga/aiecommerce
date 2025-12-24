import logging
import os
from typing import Optional

import instructor
from openai import OpenAI

from aiecommerce.models import ProductMaster

from .schemas import ProductSpecUnion

logger = logging.getLogger(__name__)


class ProductEnrichmentService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the service with an Instructor client pointing to OpenRouter.
        """
        # Fetch API key from arguments or environment
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Enrichment service will fail if called.")

        # Initialize the OpenAI client pointing to OpenRouter
        base_client = OpenAI(
            base_url=os.environ.get("OPENROUTER_BASE_URL"),
            api_key=self.api_key,
        )

        # Wrap with Instructor to enable structured output (response_model)
        self.client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)

        # Model selection:
        # "openai/gpt-4o-mini" is currently the best balance of cost/speed/accuracy for JSON extraction.
        self.model_name = os.environ.get("OPENROUTER_CLASSIFICATION_MODEL")

    def enrich_product_specs(self, product: ProductMaster) -> bool:
        """
        Analyzes the product's text fields, extracts structured specifications,
        and saves them to the 'specs' JSONField.

        Returns:
            bool: True if successful, False otherwise.
        """
        # 1. Prepare the input context
        # We combine code, description, and existing category to give the LLM maximum context.
        parts = [
            str(product.code) if product.code else "",
            str(product.description) if product.description else "",
            str(product.category) if product.category else "",
        ]
        text_to_analyze = " ".join(parts).strip()

        if not text_to_analyze:
            logger.warning(f"Product {product.id} has no text data to analyze. Skipping.")
            return False

        try:
            # 2. Call the LLM with Instructor
            # The 'response_model' argument tells Instructor to enforce our Union schema.
            extracted_data: ProductSpecUnion = self.client.chat.completions.create(
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
                    {"role": "user", "content": f"Product Text: {text_to_analyze}"},
                ],
                # OpenRouter metadata (optional but recommended)
                extra_headers={
                    "HTTP-Referer": "https://localhost:8000",  # Replace with your production domain
                    "X-Title": "AI Ecommerce Enrichment",
                },
            )

            # 3. Save to Database
            # Convert Pydantic model to a standard dict, removing empty keys to save DB space
            product.specs = extracted_data.model_dump(exclude_none=True)

            # Use update_fields to avoid race conditions with other fields
            product.save(update_fields=["specs"])

            logger.info(f"Successfully enriched Product {product.id} ({product.code}) " f"as category '{extracted_data.category_type}'")
            return True

        except Exception as e:
            logger.error(f"Failed to enrich product {product.id} ({product.code}): {e}", exc_info=True)
            return False
