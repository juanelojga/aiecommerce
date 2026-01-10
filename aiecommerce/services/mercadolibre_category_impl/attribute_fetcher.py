import logging
from typing import Dict, List

from aiecommerce.services.mercadolibre_impl import MercadoLibreClient

logger = logging.getLogger(__name__)


class MercadolibreCategoryAttributeFetcher:
    """
    Fetches and filters category attributes from the Mercado Libre API.

    This service is responsible for retrieving attributes for a given category
    and identifying which of them are mandatory for listing a product.
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
        Retrieves all attributes for a category and filters for required ones.

        An attribute is considered required if its 'tags' list contains
        'required', 'new_required', or 'conditional_required'.

        Args:
            category_id: The Mercado Libre category ID.

        Returns:
            A list of attribute dictionaries that are considered required.
            Returns an empty list if the API call fails or no required
            attributes are found.
        """
        required_tags = {"required", "new_required", "conditional_required"}
        required_attributes: List[Dict] = []

        try:
            logger.info(f"Fetching attributes for category_id: {category_id}")
            attributes = self.client.get(f"categories/{category_id}/attributes")

            if not isinstance(attributes, list):
                logger.warning(f"Expected a list of attributes, but got {type(attributes)}")
                return []

            for attr in attributes:
                attr_tags = attr.get("tags", [])
                if any(tag in attr_tags for tag in required_tags):
                    required_attributes.append(attr)

            logger.info(f"Found {len(required_attributes)} required attributes for category_id: {category_id}")
            return required_attributes
        except Exception as e:
            logger.error(
                f"Error fetching attributes for category_id {category_id}: {e}",
                exc_info=True,
            )
            return []
