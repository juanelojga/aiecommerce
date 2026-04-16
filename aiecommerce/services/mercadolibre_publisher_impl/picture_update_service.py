from __future__ import annotations

import logging

from django.utils import timezone

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient

logger = logging.getLogger(__name__)

GENERIC_IMAGE_SUFFIX = "tecnomega-image_1.jpg"


class MercadoLibrePictureUpdateService:
    """Pushes the current ProductImage set of a listing to Mercado Libre."""

    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._ml_client = ml_client

    def update_pictures(self, listing: MercadoLibreListing) -> None:
        if not listing.ml_id:
            logger.warning("Listing %s has no ml_id; skipping picture update.", listing.pk)
            return

        images = list(listing.product_master.images.all().order_by("order"))

        if not images:
            logger.warning(
                "Listing %s (product %s) has no ProductImage rows; skipping picture update.",
                listing.ml_id,
                listing.product_master.code,
            )
            return

        if any(img.url.endswith(GENERIC_IMAGE_SUFFIX) for img in images):
            logger.warning(
                "Listing %s (product %s) still has a generic %s image after refresh; skipping ML picture update.",
                listing.ml_id,
                listing.product_master.code,
                GENERIC_IMAGE_SUFFIX,
            )
            return

        payload = {"pictures": [{"source": img.url} for img in images]}
        logger.info("Updating pictures for listing %s with %d image(s).", listing.ml_id, len(images))

        try:
            self._ml_client.put(f"items/{listing.ml_id}", json=payload)
        except Exception as exc:
            logger.error("Failed to update pictures for listing %s: %s", listing.ml_id, exc)
            listing.status = MercadoLibreListing.Status.ERROR
            listing.sync_error = f"Picture update failed: {exc}"
            listing.save(update_fields=["status", "sync_error", "updated_at"])
            raise

        listing.last_synced = timezone.now()
        listing.sync_error = None
        listing.save(update_fields=["last_synced", "sync_error", "updated_at"])
        logger.info("Successfully updated pictures for listing %s.", listing.ml_id)
