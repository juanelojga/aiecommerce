import logging
from typing import Dict, List

from aiecommerce.services.mercadolibre_impl import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadolibreCategoryAttributeFetcher:
    """
    Fetches category attributes from the Mercado Libre API.

    This service is responsible for retrieving attributes for a given category.
    """

    def __init__(self, client: MercadoLibreClient):
        """
        Initializes the service with a MercadoLibreClient instance.

        Args:
            client: An instance of MercadoLibreClient to make API requests.
        """
        self.client = client

    def get_category_attributes(self, category_id: str) -> List[Dict]:
        """
        Retrieves all attributes for a category.

        Args:
            category_id: The Mercado Libre category ID.

        Returns:
            A list of attribute dictionaries
        """
        try:
            logger.info(f"Fetching attributes for category_id: {category_id}")
            attributes = self.client.get(f"categories/{category_id}/attributes")

            if not isinstance(attributes, list):
                logger.warning(f"Expected a list of attributes, but got {type(attributes)}")
                return []

            return attributes
        except Exception as e:
            logger.error(
                f"Error fetching attributes for category_id {category_id}: {e}",
                exc_info=True,
            )
            return []
