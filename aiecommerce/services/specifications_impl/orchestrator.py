import logging
from typing import Any

from aiecommerce.models import ProductMaster
from aiecommerce.services.specifications_impl.exceptions import EnrichmentError
from aiecommerce.services.specifications_impl.service import ProductSpecificationsService

logger = logging.getLogger(__name__)


class ProductSpecificationsOrchestrator:
    """
    Orchestrates the enrichment process for a single product.
    """

    def __init__(self, service: ProductSpecificationsService):
        """Initialize with a specifications service.

        Args:
            service: The service for enriching product specifications.
        """
        self.service = service

    def process_product(self, product: ProductMaster, dry_run: bool) -> tuple[bool, Any | None]:
        """Process a single product for specification enrichment.

        Args:
            product: The ProductMaster instance to process.
            dry_run: If True, data is not saved to the database.

        Returns:
            A tuple of (success boolean, extracted specs dict or None).
        """
        try:
            product_data = {
                "code": product.code,
                "description": product.description,
                "category": product.category,
            }
            extracted_specs = self.service.enrich_product(product_data)

            if not extracted_specs:
                logger.warning(f"Product {product.id}: Failed to extract specs (no data returned).")
                return False, None

            if extracted_specs:
                # Extract direct fields for better database access
                product.model_name = extracted_specs.model_name
                product.normalized_name = extracted_specs.normalized_name

                # Save full JSON as well
                specs_dict = extracted_specs.model_dump(exclude_none=True)
                product.specs = specs_dict

                if not dry_run:
                    product.save(update_fields=["specs", "model_name", "normalized_name"])
                return True, specs_dict
            return False, None

        except EnrichmentError as e:
            logger.error(f"Product {product.id}: Service Error - {e}")
            return False, None
        except Exception as e:
            logger.error(f"Product {product.id}: An unexpected error occurred - {e}", exc_info=True)
            return False, None
