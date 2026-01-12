import logging
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError

logger = logging.getLogger(__name__)


class MercadoLibrePublisherService:
    """
    Handles the publication of products to Mercado Libre.
    """

    def __init__(self, client: MercadoLibreClient):
        self.client = client

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

    def publish_product(self, product: ProductMaster, dry_run: bool = False, test: bool = False) -> Dict[str, Any]:
        """
        Executes the publication process.
        1. Create item (POST /items)
        2. Create description (POST /items/{id}/description)
        """

        payload = self.build_payload(product, test=test)

        if dry_run:
            logger.info(f"[Dry-Run] Payload for product {product.code} generated.")
            return {"dry_run": True, "payload": payload}

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

            logger.info(f"Successfully published product {product.code} as {ml_id}")
            return item_response

        except MLAPIError as e:
            error_msg = f"Failed to publish {product.code}: {str(e)}"
            logger.error(error_msg)

            # Record error in the listing
            listing = product.mercadolibre_listing
            listing.status = MercadoLibreListing.Status.ERROR
            listing.sync_error = str(e)
            listing.save()

            raise
