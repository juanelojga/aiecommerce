import logging

from eansearch import EANSearch

logger = logging.getLogger(__name__)


class EANSearchClient:
    """
    Implements the Tier 2 GTIN discovery strategy via the ean-search.org API.
    """

    def __init__(self, api_token: str):
        self.client = EANSearch(token=api_token)

    def find_gtin(self, description: str) -> str | None:
        """
        Searches for a GTIN (EAN) for a given product description.

        Args:
            description: The product description to search for.

        Returns:
            The EAN string if found, otherwise None.
        """
        try:
            results = self.client.productSearch(description)
            if results and len(results) > 0:
                return results[0].get("ean")
            logger.info("No results from ean-search for description: %s", description)
            return None
        except Exception as e:
            logger.error(
                "Error calling ean-search API for description '%s': %s",
                description,
                e,
                exc_info=True,
            )
            return None
