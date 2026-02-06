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

    MAX_RETRY_ATTEMPTS = 2  # Original try + 1 retry

    def __init__(self, client: MercadoLibreClient, attribute_fixer: MercadolibreAttributeFixer):
        self.client = client
        self.attribute_fixer = attribute_fixer

    def build_payload(self, product: ProductMaster, test: bool = False) -> Dict[str, Any]:
        """Construct the JSON payload for the POST /items endpoint.

        Args:
            product: The master product to publish.
            test: Whether to create a test listing.

        Returns:
            Dictionary containing the payload for the Mercado Libre API.
        """
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
        """Extract the JSON body from an HTTP Error 400 response.

        Args:
            error_str: The error string containing the HTTP error.

        Returns:
            The JSON body if found, None otherwise.
        """
        match = re.search(r"HTTP Error 400: (\{.*\})", error_str)
        return match.group(1) if match else None

    def _is_validation_error(self, error_str: str, attempt: int) -> bool:
        """Check if the error is a 400 validation error eligible for retry.

        Args:
            error_str: The error string to check.
            attempt: The current attempt number.

        Returns:
            True if the error is a validation error on the first attempt.
        """
        return "HTTP Error 400" in error_str and attempt == 1 and self.attribute_fixer is not None

    def _try_fix_attributes(self, product: ProductMaster, error_str: str) -> bool:
        """Attempt to fix attributes using the AI attribute fixer.

        Args:
            product: The product to fix attributes for.
            error_str: The error string containing validation details.

        Returns:
            True if attributes were successfully fixed, False otherwise.
        """
        error_json = self._extract_error_body(error_str)
        listing = product.mercadolibre_listing

        try:
            fixed_attributes = self.attribute_fixer.fix_attributes(product, listing.attributes or [], error_json or error_str)

            # Save fixed attributes to DB so build_payload uses them in the retry
            listing.attributes = fixed_attributes
            listing.save()

            logger.info(f"Attributes fixed for {product.code}. Retrying...")
            return True
        except Exception as fix_err:
            logger.error(f"AI Attribute Fixer failed: {fix_err}")
            return False

    def _mark_listing_success(self, product: ProductMaster, ml_id: str) -> None:
        """Update the listing record after successful publication.

        Args:
            product: The product whose listing to update.
            ml_id: The Mercado Libre item ID.
        """
        with transaction.atomic():
            listing = product.mercadolibre_listing
            listing.ml_id = ml_id
            listing.status = MercadoLibreListing.Status.ACTIVE
            listing.last_synced = timezone.now()
            listing.sync_error = None
            listing.save()

    def _mark_listing_failed(self, product: ProductMaster, error_str: str) -> None:
        """Update the listing record after failed publication.

        Args:
            product: The product whose listing to update.
            error_str: The error message to record.
        """
        listing = product.mercadolibre_listing
        listing.status = MercadoLibreListing.Status.ERROR
        listing.sync_error = error_str
        listing.save()

    def _publish_to_api(self, product: ProductMaster, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the API calls to publish a product.

        Args:
            product: The product being published.
            payload: The JSON payload for the item endpoint.

        Returns:
            The API response from creating the item.

        Raises:
            MLAPIError: If the API call fails.
        """
        # Step 1: Create the Listing
        item_response = self.client.post("items", json=payload)
        ml_id = item_response.get("id")

        # Step 2: Add the Description
        description_payload = {"plain_text": product.seo_description or ""}
        self.client.post(f"items/{ml_id}/description", json=description_payload)

        return item_response

    def publish_product(self, product: ProductMaster, dry_run: bool = False, test: bool = False) -> Optional[Dict[str, Any]]:
        """Publish a product to Mercado Libre with retry logic for validation errors.

        Args:
            product: The master product to publish.
            dry_run: If True, only log the payload without making API calls.
            test: Whether to create a test listing.

        Returns:
            The API response if successful, None if dry_run.

        Raises:
            MLAPIError: If publication fails after all retries.
        """
        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            payload = self.build_payload(product, test=test)

            if dry_run:
                logger.info(f"[Dry-Run] Payload generated: {payload}")
                return None

            try:
                item_response = self._publish_to_api(product, payload)
                ml_id = item_response.get("id")
                if ml_id:
                    self._mark_listing_success(product, ml_id)
                return item_response

            except MLAPIError as e:
                error_str = str(e)

                # Check for 400 Validation Error on first attempt
                if self._is_validation_error(error_str, attempt):
                    logger.warning(f"Validation error for {product.code}. Attempting AI fix...")
                    if self._try_fix_attributes(product, error_str):
                        continue  # Re-run the loop with fixed attributes

                # Final Failure handling
                error_msg = f"Failed to publish {product.code}: {error_str}"
                logger.error(error_msg)
                self._mark_listing_failed(product, error_str)
                raise

        return None
