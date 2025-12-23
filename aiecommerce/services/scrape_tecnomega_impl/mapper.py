# --- services/scrape_tecnomega_impl/mapper.py ---
import logging
from typing import Dict, List, Optional

from aiecommerce.models.product import ProductRawWeb

logger = logging.getLogger(__name__)


class ProductMapper:
    """Maps raw extracted data to ProductRawWeb model instances."""

    def to_entity(
        self,
        raw_product: Dict[str, Optional[str]],
        scrape_session_id: str,
        search_term: str,
    ) -> ProductRawWeb:
        """
        Transforms a single raw product dictionary into a ProductRawWeb object.
        """
        return ProductRawWeb(
            distributor_code=raw_product.get("distributor_code"),
            raw_description=raw_product.get("raw_description"),
            stock_principal=raw_product.get("stock_principal"),
            stock_colon=raw_product.get("stock_colon"),
            stock_sur=raw_product.get("stock_sur"),
            stock_gye_norte=raw_product.get("stock_gye_norte"),
            stock_gye_sur=raw_product.get("stock_gye_sur"),
            image_url=raw_product.get("image_url", ""),
            scrape_session_id=scrape_session_id,
            search_term=search_term,
        )

    def map_to_models(
        self,
        raw_products: List[Dict[str, Optional[str]]],
        scrape_session_id: str,
        search_term: str,
    ) -> List[ProductRawWeb]:
        """
        Transforms a list of raw product dictionaries into a list of ProductRawWeb objects.

        Args:
            raw_products: List of dictionaries from the parser.
            scrape_session_id: The unique identifier for the current scraping session.
            search_term: The category or term used for the search.

        Returns:
            A list of ProductRawWeb model instances ready for persistence.
        """
        if not raw_products:
            return []

        logger.info(f"Mapping {len(raw_products)} raw products for search term '{search_term}'.")

        products_to_create = []
        for raw_product in raw_products:
            # Basic cleaning and type conversion can be done here if necessary,
            # but for now, we are mapping strings to strings as per the model definition.
            product = ProductRawWeb(
                distributor_code=raw_product.get("distributor_code"),
                raw_description=raw_product.get("raw_description"),
                stock_principal=raw_product.get("stock_principal"),
                stock_colon=raw_product.get("stock_colon"),
                stock_sur=raw_product.get("stock_sur"),
                stock_gye_norte=raw_product.get("stock_gye_norte"),
                stock_gye_sur=raw_product.get("stock_gye_sur"),
                image_url=raw_product.get("image_url", ""),
                scrape_session_id=scrape_session_id,
                search_term=search_term,
            )
            products_to_create.append(product)

        logger.info(f"Successfully mapped {len(products_to_create)} products to model instances.")
        return products_to_create
