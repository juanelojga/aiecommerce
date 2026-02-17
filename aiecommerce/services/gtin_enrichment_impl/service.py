"""GTIN enrichment service using LLM with online search capabilities."""

import logging
import re
from typing import Any

import instructor
from django.conf import settings
from openai import APIError, OpenAI
from pydantic import ValidationError

from aiecommerce.models import ProductMaster

from .exceptions import ConfigurationError
from .schemas import GTINSearchResult

logger = logging.getLogger(__name__)

# Strategy names
STRATEGY_SKU_NAME = "sku_normalized_name"
STRATEGY_MODEL_BRAND = "model_brand"
STRATEGY_RAW_DESCRIPTION = "raw_description"
STRATEGY_NOT_FOUND = "NOT_FOUND"


class GTINSearchService:
    """Service to search for GTIN codes using LLM with online search."""

    def __init__(self) -> None:
        """
        Initialize the GTIN search service.

        Raises:
            ConfigurationError: If required settings are missing.
        """
        # Validate configuration
        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL
        self.model_name = settings.GTIN_SEARCH_MODEL

        if not all([api_key, base_url, self.model_name]):
            raise ConfigurationError("The following settings are required: OPENROUTER_API_KEY, OPENROUTER_BASE_URL, GTIN_SEARCH_MODEL")

        # Initialize OpenAI client pointing to OpenRouter
        base_client = OpenAI(base_url=base_url, api_key=api_key)
        # Wrap with Instructor for structured output
        self.client: Any = instructor.from_openai(base_client, mode=instructor.Mode.JSON)

    def search_gtin(self, product: ProductMaster) -> tuple[str | None, str]:
        """
        Search for a GTIN code using three sequential strategies.

        Args:
            product: The ProductMaster instance to search GTIN for.

        Returns:
            A tuple of (gtin_code, strategy_name).
            Returns (None, "NOT_FOUND") if all strategies fail.
        """
        logger.info(f"Starting GTIN search for product code: {product.code}")

        # Strategy 1: SKU + Normalized Name
        gtin = self._search_with_sku_and_name(product)
        if gtin:
            logger.info(f"GTIN found using strategy '{STRATEGY_SKU_NAME}': {gtin}")
            return gtin, STRATEGY_SKU_NAME

        # Strategy 2: Model Name + Brand
        gtin = self._search_with_model_and_brand(product)
        if gtin:
            logger.info(f"GTIN found using strategy '{STRATEGY_MODEL_BRAND}': {gtin}")
            return gtin, STRATEGY_MODEL_BRAND

        # Strategy 3: Raw Description from ProductDetailScrape
        gtin = self._search_with_raw_description(product)
        if gtin:
            logger.info(f"GTIN found using strategy '{STRATEGY_RAW_DESCRIPTION}': {gtin}")
            return gtin, STRATEGY_RAW_DESCRIPTION

        logger.warning(f"No GTIN found for product code: {product.code}")
        return None, STRATEGY_NOT_FOUND

    def _search_with_sku_and_name(self, product: ProductMaster) -> str | None:
        """
        Strategy 1: Search using SKU and normalized name.

        Args:
            product: The ProductMaster instance.

        Returns:
            GTIN code if found, None otherwise.
        """
        if not product.sku or not product.normalized_name:
            logger.debug(f"Skipping strategy '{STRATEGY_SKU_NAME}': missing SKU or normalized_name for product {product.code}")
            return None

        query = f"SKU: {product.sku}, Product: {product.normalized_name}"
        return self._execute_search(query, STRATEGY_SKU_NAME)

    def _search_with_model_and_brand(self, product: ProductMaster) -> str | None:
        """
        Strategy 2: Search using model name and brand from specs.

        Args:
            product: The ProductMaster instance.

        Returns:
            GTIN code if found, None otherwise.
        """
        if not product.model_name:
            logger.debug(f"Skipping strategy '{STRATEGY_MODEL_BRAND}': missing model_name for product {product.code}")
            return None

        brand = None
        if product.specs and isinstance(product.specs, dict):
            # Try different brand field names
            brand = product.specs.get("Brand") or product.specs.get("brand") or product.specs.get("Marca")

        if not brand:
            logger.debug(f"Skipping strategy '{STRATEGY_MODEL_BRAND}': missing Brand in specs for product {product.code}")
            return None

        query = f"Brand: {brand}, Model: {product.model_name}"
        return self._execute_search(query, STRATEGY_MODEL_BRAND)

    def _search_with_raw_description(self, product: ProductMaster) -> str | None:
        """
        Strategy 3: Search using raw description from ProductDetailScrape.

        Args:
            product: The ProductMaster instance.

        Returns:
            GTIN code if found, None otherwise.
        """
        # Get the most recent detail scrape
        detail_scrape = product.detail_scrapes.order_by("-created_at").first()

        if not detail_scrape:
            logger.debug(f"Skipping strategy '{STRATEGY_RAW_DESCRIPTION}': no ProductDetailScrape found for product {product.code}")
            return None

        # Try to construct a meaningful description from available fields
        parts = []
        if detail_scrape.name:
            parts.append(detail_scrape.name)

        # Add attributes if available
        if detail_scrape.attributes and isinstance(detail_scrape.attributes, dict):
            for key, value in detail_scrape.attributes.items():
                if value and str(value).strip():
                    parts.append(f"{key}: {value}")

        if not parts:
            logger.debug(f"Skipping strategy '{STRATEGY_RAW_DESCRIPTION}': no usable data in ProductDetailScrape for product {product.code}")
            return None

        query = " | ".join(parts[:5])  # Limit to first 5 parts to avoid too long queries
        return self._execute_search(query, STRATEGY_RAW_DESCRIPTION)

    def _execute_search(self, query: str, strategy_name: str) -> str | None:
        """
        Execute the LLM search with the given query.

        Args:
            query: The search query string.
            strategy_name: Name of the strategy being used (for logging).

        Returns:
            GTIN code if found and valid, None otherwise.
        """
        try:
            logger.debug(f"Executing search for strategy '{strategy_name}' with query: {query}")

            # Call LLM with online search capabilities
            result: GTINSearchResult = self.client.chat.completions.create(
                model=self.model_name,
                response_model=GTINSearchResult,
                parallel_tool_calls=False,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a product identification expert with access to online search. "
                            "Your task is to find the GTIN (EAN/UPC) code for the given product. "
                            "GTIN codes are 8-14 digit numbers used to uniquely identify products globally. "
                            "Search online databases, manufacturer websites, and e-commerce sites to find the exact GTIN. "
                            "IMPORTANT RULES:\n"
                            "1. Return ONLY valid GTIN codes (8-14 digits, numeric only).\n"
                            "2. Do NOT return partial codes, model numbers, or SKUs.\n"
                            "3. If you cannot find a valid GTIN, return null for the gtin field.\n"
                            "4. Set confidence to 'high' only if you found the GTIN on the manufacturer's official site or verified database.\n"
                            "5. Set confidence to 'medium' if found on a major e-commerce site.\n"
                            "6. Set confidence to 'low' if found on user-generated content or unverified sources.\n"
                            "7. Include the source URL where you found the GTIN."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Find the GTIN/EAN/UPC code for this product:\n{query}",
                    },
                ],
                extra_headers={
                    "HTTP-Referer": "https://localhost:8000",
                    "X-Title": "AI Ecommerce GTIN Search",
                },
            )

            # Validate the GTIN format
            if result.gtin:
                if self._validate_gtin(result.gtin):
                    logger.info(f"Valid GTIN found: {result.gtin} (confidence: {result.confidence}, source: {result.source})")
                    return result.gtin
                else:
                    logger.warning(f"Invalid GTIN format returned: {result.gtin}")
                    return None

            logger.debug(f"No GTIN found for strategy '{strategy_name}'")
            return None

        except (APIError, TimeoutError) as e:
            logger.error(f"API/Network error during search (strategy '{strategy_name}'): {e}", exc_info=True)
            return None
        except ValidationError as e:
            logger.error(
                f"Validation error during search (strategy '{strategy_name}'): Could not parse LLM response. {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.critical(
                f"Unexpected error during search (strategy '{strategy_name}'): {e}",
                exc_info=True,
            )
            return None

    def _validate_gtin(self, gtin: str) -> bool:
        """
        Validate that the GTIN is a numeric string with 8-14 digits.

        Args:
            gtin: The GTIN string to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not gtin:
            return False

        # Check if it's numeric and has correct length
        pattern = r"^\d{8,14}$"
        return bool(re.match(pattern, gtin))
