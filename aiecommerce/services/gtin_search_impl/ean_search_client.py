import logging
from typing import Any, Dict, Generator

import requests
from django.conf import settings
from eansearch import EANSearch

logger = logging.getLogger(__name__)


class EANSearchClient:
    """
    Implements the Tier 2 GTIN discovery strategy via the ean-search.org API.
    """

    def __init__(self) -> None:
        self.client = EANSearch(token=settings.EAN_SEARCH_TOKEN)

    def search_products_lazy(self, query: str) -> Generator[Dict[str, Any], None, None]:
        """
        Searches for products using the given query and yields results page by page.

        Args:
            query: The search query.

        Yields:
            A dictionary representing a page of product results.
        """
        page = 0
        while True:
            try:
                # EANSearch class has productSearch(self, name, page=0, lang=1)
                product_list = self.client.productSearch(query, page=page)

                # The eansearch library 1.8.3 productSearch returns only the product list.
                # If we have products, we yield them and try the next page.
                # If productSearch returns an empty list or something else, we stop.
                if not product_list or not isinstance(product_list, list):
                    break

                response = {"productlist": product_list}
                yield response

                # Arbitrary limit to avoid infinite loops if API always returns something
                if page > 10:
                    break

                page += 1
            except requests.exceptions.Timeout:
                logger.warning("Timeout occurred during eansearch for query '%s' on page %d", query, page)
                break
            except Exception as e:
                logger.error(
                    "An error occurred during eansearch for query '%s' on page %d: %s",
                    query,
                    page,
                    e,
                    exc_info=True,
                )
                break
