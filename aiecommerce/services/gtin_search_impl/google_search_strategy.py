"""
This module defines the Google Search strategy for finding GTINs.
"""

import logging
import re
from typing import Any

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.google_search_client import (
    GoogleSearchClient,
)

logger = logging.getLogger(__name__)


class GoogleGTINStrategy:
    """
    Strategy to find a Global Trade Item Number (GTIN) for a product using Google Search.

    This strategy employs a waterfall approach, trying several query formulations.
    """

    def __init__(self, google_client: GoogleSearchClient):
        """
        Initializes the strategy with a Google Search client.

        Args:
            google_client: An instance of a client to interact with a Google Search service.
        """
        self.google_client = google_client
        self.ean_pattern = re.compile(r"\b(\d{12,14})\b")

    def _get_clean_sku(self, sku: str) -> str:
        """Returns the SKU part before the first underscore."""
        return sku.split("_")[0]

    def _extract_from_snippets(self, search_results: Any) -> str | None:
        """
        Extracts a 12 to 14-digit EAN code from search result snippets.

        It iterates through search items and uses regex to find a potential GTIN.

        Args:
            search_results: The raw results from the Google Search client. Expected to be a
                            dictionary with an 'items' key containing a list of results.

        Returns:
            The first valid GTIN found, or None if no GTIN is found.
        """
        if not search_results or "items" not in search_results:
            return None

        for item in search_results["items"]:
            snippet = item.get("snippet", "")
            if not snippet:
                continue

            match = self.ean_pattern.search(snippet)
            if match:
                logger.debug(f"Found potential GTIN '{match.group(1)}' in snippet.")
                return match.group(1)

        return None

    def execute(self, product: ProductMaster) -> dict[str, str] | None:
        """
        Executes a series of Google searches to find a GTIN for the given product.

        The method tries three different search queries in order:
        1. A general query with category, cleaned SKU, and logistics keywords.
        2. A targeted search on 'icecat.biz' with category and cleaned SKU.
        3. A dynamic query built from the product's specifications if available.

        Args:
            product: The ProductMaster instance for which to find a GTIN.

        Returns:
            A dictionary containing the 'gtin' and 'source' if a GTIN is found,
            otherwise None.
        """
        raw_sku = product.sku
        if not raw_sku:
            logger.warning(f"Product {product.id} has no SKU. Skipping SKU-based Google searches.")
            cleaned_sku = ""
        else:
            cleaned_sku = self._get_clean_sku(raw_sku)
            logger.info(f"Starting GTIN search for Raw SKU: '{raw_sku}', Cleaned SKU: '{cleaned_sku}'")

        # Search 1: General logistics query
        if cleaned_sku:
            query1 = f"{product.category or ''} {cleaned_sku} EAN GTIN barcode".strip()
            logger.info(f"Attempt 1: Attempting GTIN search with query: '{query1}'")
            search_results = self.google_client.list(q=query1)
            if code := self._extract_from_snippets(search_results):
                logger.info(f"Success: Found GTIN '{code}' with query: '{query1}'")
                return {"gtin": code, "source": "google_search"}

            # Search 2: Icecat targeted query
            query2 = f"site:icecat.biz {product.category or ''} {cleaned_sku}".strip()
            logger.info(f"Attempt 2: Attempting GTIN search with query: '{query2}'")
            search_results = self.google_client.list(q=query2)
            if code := self._extract_from_snippets(search_results):
                logger.info(f"Success: Found GTIN '{code}' with query: '{query2}'")
                return {"gtin": code, "source": "google_search"}

        # Search 3: Specs-based dynamic query
        if product.specs:
            specs_keys = [
                product.specs.get("manufacturer"),
                product.specs.get("model_name"),
                product.specs.get("cpu"),  # For Notebooks, Desktops, Processors
                product.specs.get("chipset"),  # For GPUs, Motherboards
                product.specs.get("ram"),  # For Notebooks, Desktops
                product.specs.get("capacity"),  # For Storage, RAM
            ]
            dynamic_query_parts = [str(part) for part in [product.category] + specs_keys if part]

            if len(dynamic_query_parts) > 1:
                query3 = " ".join(dynamic_query_parts)
                logger.info(f"Attempt 3: Attempting GTIN search with specs-based query: '{query3}'")
                search_results = self.google_client.list(q=query3)
                if code := self._extract_from_snippets(search_results):
                    logger.info(f"Success: Found GTIN '{code}' with query: '{query3}'")
                    return {"gtin": code, "source": "google_search"}

        logger.warning(f"No GTIN found for product Raw SKU: {raw_sku} after all Google Search attempts.")
        return None
