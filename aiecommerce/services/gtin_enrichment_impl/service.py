"""GTIN enrichment service.

This module provides a small service that attempts to discover a product's
GTIN (EAN/UPC) by using an LLM with online-search capabilities. The service
applies several ordered search strategies (from the most-specific to the
most-general) and validates candidate GTINs before accepting them.

Behavioral notes:
- Strategies are attempted sequentially; the first successful result is
    returned along with the strategy identifier.
- All GTINs are validated to be numeric strings containing 8–14 digits.
- The LLM is expected to return a simple JSON-like response mapped to the
    `GTINSearchResult` pydantic model. Parsing/validation errors are caught and
    logged; failures return (None, STRATEGY_NOT_FOUND).
"""

import logging
import re

import instructor
from django.conf import settings
from openai import APIError
from pydantic import ValidationError

from aiecommerce.models import ProductMaster

from .schemas import GTINSearchResult

logger = logging.getLogger(__name__)

# Strategy names
STRATEGY_SKU_NAME = "sku_normalized_name"
STRATEGY_MODEL_BRAND = "model_brand"
STRATEGY_RAW_DESCRIPTION = "raw_description"
STRATEGY_NOT_FOUND = "NOT_FOUND"


class GTINSearchService:
    """Search service that tries several heuristics to find a GTIN.

    The service encapsulates three heuristics (strategies) aimed at finding
    a GTIN for a `ProductMaster` record. Each strategy builds a compact
    search query and asks the LLM (with online/search tools) to locate a
    GTIN. If a GTIN is returned, it is validated and, when valid, returned
    with the strategy name.

    The public API is `search_gtin(product)` which returns a tuple:
    `(gtin: str | None, strategy_name: str)`.
    """

    def __init__(self, client: instructor.Instructor) -> None:
        self.client = client

    def search_gtin(self, product: ProductMaster) -> tuple[str | None, str]:
        """Attempt to locate a GTIN for `product` using ordered strategies.

        The method runs three strategies in order and returns as soon as one
        produces a valid GTIN. If none succeed the method returns
        `(None, STRATEGY_NOT_FOUND)`.

        Args:
            product: ProductMaster instance to enrich.

        Returns:
            (gtin, strategy): `gtin` is the discovered GTIN string or `None`.
            `strategy` is one of the `STRATEGY_*` constants indicating which
            heuristic produced the result (or `STRATEGY_NOT_FOUND`).
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
        """Strategy #1 — query by SKU and normalized product name.

        This is the most specific strategy: combining SKU (if present) with
        the normalized human-readable product name usually yields precise
        search results on manufacturer or retail sites.
        """
        if not product.sku or not product.normalized_name:
            logger.debug(f"Skipping strategy '{STRATEGY_SKU_NAME}': missing SKU or normalized_name for product {product.code}")
            return None

        query = f"SKU: {product.sku}, Product: {product.normalized_name}"
        return self._execute_search(query, STRATEGY_SKU_NAME)

    def _search_with_model_and_brand(self, product: ProductMaster) -> str | None:
        """Strategy #2 — query by `model_name` plus brand pulled from specs.

        Many products expose `model_name` in their specs; when paired with the
        brand this frequently identifies the exact item. We attempt several
        common brand keys inside the `specs` dict (e.g. "Brand", "brand",
        "Marca"). If no brand is present the strategy is skipped.
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
        """Strategy #3 — build a query from the latest scraped product details.

        Falls back to the most recent `ProductDetailScrape` and composes a
        compact description using the scraped `name` and up to the first
        few non-empty attributes. This is the broadest and least-precise
        strategy, used when structured fields (SKU, model, brand) are
        unavailable.
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
        """Run the LLM online search and return a validated GTIN or None.

        This method sends a compact prompt to the LLM (configured via
        `settings.GTIN_SEARCH_MODEL`) expecting a simple response that maps
        to `GTINSearchResult`. It handles network/API errors and response
        validation; on any failure it returns `None` and logs an appropriate
        message.
        """
        try:
            logger.debug(f"Executing search for strategy '{strategy_name}' with query: {query}")

            # Call the LLM which is expected to perform online searches
            # and return a simple result matching `GTINSearchResult`.
            result: GTINSearchResult = self.client.chat.completions.create(
                model=settings.GTIN_SEARCH_MODEL,
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
                            "7. Include the source URL where you found the GTIN.\n\n"
                            "EXAMPLE RESPONSE FORMAT:\n"
                            "{\n"
                            '  "gtin": "0123456789012",\n'
                            '  "confidence": "high",\n'
                            '  "source": "https://www.example.com/product"\n'
                            "}\n\n"
                            'CRITICAL: Return string values directly. DO NOT use nested objects like {"type": "string", "value": "..."}.'
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Find the GTIN/EAN/UPC code for this product:\n{query}",
                    },
                ],
            )

            # If the model returned a candidate GTIN, validate its format
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
            # Transient network or API-level error — skip this attempt.
            logger.error(f"API/Network error during search (strategy '{strategy_name}'): {e}", exc_info=True)
            return None
        except ValidationError as e:
            # The LLM response did not conform to the expected schema.
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
        """Return True if `gtin` is a numeric string of length 8–14.

        This performs only a syntactic check (digits + length). It does not
        perform checksum validation (e.g. modulo 10) because some GTIN-like
        identifiers used in external sources may not strictly follow that
        rule; leaving checksum validation out reduces false negatives.
        """
        if not gtin:
            return False

        # Check if it's numeric and has correct length
        pattern = r"^\d{8,14}$"
        return bool(re.match(pattern, gtin))
