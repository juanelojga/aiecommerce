"""
This module defines the Google Search strategy for finding GTINs.
"""

import logging
import re
from typing import Any

from aiecommerce.models.product import ProductMaster

logger = logging.getLogger(__name__)


class GoogleGTINStrategy:
    """
    Strategy to find a Global Trade Item Number (GTIN) for a product using Google Search.

    This strategy employs a waterfall approach, trying several query formulations.
    """

    def __init__(self, google_client: Any, search_engine_id: str | None = None):
        """
        Initializes the strategy with a Google Search client.

        Args:
            google_client: An instance of a client to interact with a Google Search service.
            search_engine_id: The Google Custom Search Engine ID (cx).
        """
        self.google_client = google_client
        self.search_engine_id = search_engine_id
        self.ean_pattern = re.compile(r"\b(\d{12,14})\b")

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
        Executes a dynamic query built from the product's specifications if available.

        Args:
            product: The ProductMaster instance for which to find a GTIN.

        Returns:
            A dictionary containing the 'gtin' and 'source' if a GTIN is found,
            otherwise None.
        """

        # Specs-based dynamic query
        if product.specs:
            specs_keys = [
                product.specs.get("manufacturer"),
                product.specs.get("model_name"),
                product.specs.get("cpu"),  # For Notebooks, Desktops, Processors
                product.specs.get("chipset"),  # For GPUs, Motherboards
                product.specs.get("ram"),  # For Notebooks, Desktops
                product.specs.get("capacity"),  # For Storage, RAM
            ]
            dynamic_query_parts = [str(part) for part in specs_keys if part]

            if len(dynamic_query_parts) > 1:
                query = " ".join(dynamic_query_parts) + " EAN GTIN barcode"
                logger.info(f"Attempting GTIN search with specs-based query: '{query}'")
                search_results = self.google_client.cse().list(q=query, cx=self.search_engine_id).execute()
                if code := self._extract_from_snippets(search_results):
                    logger.info(f"Success: Found GTIN '{code}' with query: '{query}'")
                    return {"gtin": code, "gtin_source": "google_search"}

        logger.warning(f"No GTIN found for product: {product.code} after all Google Search attempts.")
        return None
