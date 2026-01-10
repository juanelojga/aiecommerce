import logging
from typing import Optional

from .client import MercadoLibreClient
from .exceptions import MLAPIError

logger = logging.getLogger(__name__)


# TODO: Remove
class CategoryPredictorService:
    """
    Service to predict the Mercado Libre category for a given product title.
    """

    def __init__(self, client: MercadoLibreClient, site_id: str):
        self.client = client
        self.site_id = site_id

    def predict_category(self, title: str) -> Optional[str]:
        """
        Predicts the category for a given title using the Mercado Libre API.

        Args:
            title: The product title to predict the category for.

        Returns:
            The predicted category ID, or None if no prediction can be made.
        """
        if not title:
            logger.warning("Title is empty, cannot predict category.")
            return None

        try:
            response = self.client.get(f"/sites/{self.site_id}/domain_discovery/search", params={"q": title, "limit": 1})
            if response and isinstance(response, list) and response[0].get("category_id"):
                return response[0]["category_id"]
            logger.warning(f"Could not predict category for title: '{title}'. Response: {response}")
            return None
        except MLAPIError as e:
            logger.error(f"Error predicting category for title '{title}': {e}", exc_info=True)
            return None
        except (IndexError, KeyError) as e:
            logger.error(f"Unexpected response format from category predictor for title '{title}': {e}", exc_info=True)
            return None
