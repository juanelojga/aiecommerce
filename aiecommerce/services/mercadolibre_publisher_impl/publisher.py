import logging
import re
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_category_impl.attribute_fixer import MercadolibreAttributeFixer
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError

logger = logging.getLogger(__name__)


class MercadoLibrePublisherService:
    """
    Handles the publication of products to Mercado Libre.
    """

    def __init__(self, client: MercadoLibreClient, attribute_fixer: MercadolibreAttributeFixer):
        self.client = client
        self.attribute_fixer = attribute_fixer

    def build_payload(self, product: ProductMaster, test: bool = False) -> Dict[str, Any]:
        """Constructs the JSON payload for the POST /items endpoint."""
        listing = product.mercadolibre_listing

        # Build pictures list (ML requires public URLs)
        pictures = [{"source": img.url} for img in product.images.all()]

        price = float(listing.final_price) if listing.final_price is not None else 0.0

        title = "Item de test - No ofertar" if test else product.seo_title

        return {
            "title": title,
            "category_id": listing.category_id,
            "price": price,
            "currency_id": "USD",
            "available_quantity": listing.available_quantity,
            "buying_mode": "buy_it_now",
            "listing_type_id": "bronze",
            "condition": "new",
            "pictures": pictures,
            "attributes": listing.attributes,
            "sale_terms": [{"id": "WARRANTY_TYPE", "value_name": "Garantía de fábrica"}, {"id": "WARRANTY_TIME", "value_name": "12 meses"}],
        }

    def _extract_error_body(self, error_str: str) -> Optional[str]:
        """Extracts the JSON body from the 'HTTP Error 400: {...}' string."""
        match = re.search(r"HTTP Error 400: (\{.*\})", error_str)
        return match.group(1) if match else None

    def publish_product(self, product: ProductMaster, dry_run: bool = False, test: bool = False):
        """
        Executes publication with a self-healing retry for validation errors.
        """
        attempts = 0
        max_attempts = 2  # Original try + 1 retry

        while attempts < max_attempts:
            attempts += 1
            payload = self.build_payload(product, test=test)

            if dry_run:
                logger.info(f"[Dry-Run] Payload generated: {payload}")
                return

            try:
                # Step 1: Create the Listing
                item_response = self.client.post("items", json=payload)
                ml_id = item_response.get("id")

                # Step 2: Add the Description
                description_payload = {"plain_text": product.seo_description or ""}
                self.client.post(f"items/{ml_id}/description", json=description_payload)

                # Step 3: Update local record
                with transaction.atomic():
                    listing = product.mercadolibre_listing
                    listing.ml_id = ml_id
                    listing.status = MercadoLibreListing.Status.ACTIVE
                    listing.last_synced = timezone.now()
                    listing.sync_error = None
                    listing.save()

                return item_response

            except MLAPIError as e:
                error_str = str(e)
                # Check for 400 Validation Error on first attempt
                if "HTTP Error 400" in error_str and attempts == 1 and self.attribute_fixer:
                    logger.warning(f"Validation error for {product.code}. Attempting AI fix...")

                    error_json = self._extract_error_body(error_str)
                    listing = product.mercadolibre_listing

                    try:
                        fixed_attributes = self.attribute_fixer.fix_attributes(product, listing.attributes or [], error_json or error_str)

                        # Save fixed attributes to DB so build_payload uses them in the retry
                        listing.attributes = fixed_attributes
                        listing.save()

                        logger.info(f"Attributes fixed for {product.code}. Retrying...")
                        continue  # Re-run the loop with fixed attributes
                    except Exception as fix_err:
                        logger.error(f"AI Attribute Fixer failed: {fix_err}")

                # Final Failure handling
                error_msg = f"Failed to publish {product.code}: {error_str}"
                logger.error(error_msg)

                listing = product.mercadolibre_listing
                listing.status = MercadoLibreListing.Status.ERROR
                listing.sync_error = error_str
                listing.save()
                raise
        return
