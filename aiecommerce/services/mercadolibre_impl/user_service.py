from typing import Any, Dict, Optional

from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient


class MercadoLibreUserService:
    """Service to handle user-related operations in Mercado Libre."""

    def __init__(self, client: Optional[MercadoLibreClient] = None):
        self.client = client or MercadoLibreClient()

    def create_test_user(self, site_id: str) -> Dict[str, Any]:
        """
        Creates a test user for a given site.
        https://developers.mercadolibre.com/en_us/test-users
        """
        return self.client.post("/users/test_user", json={"site_id": site_id})
