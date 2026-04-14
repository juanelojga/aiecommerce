"""Remediation of MercadoLibreListing rows stuck in ERROR.

Classifies each listing's `sync_error` and applies the matching cleanup:
- Invalid/duplicate/missing GTIN: clear ProductMaster.gtin and delete the listing
- Missing price: delete the listing (ProductMaster.price is left untouched)
- Any other error: delete the listing so the next publish batch recreates it
  cleanly with the updated prompts + pre-publish guards.
"""

import logging
from typing import Optional

from aiecommerce.models.mercadolibre import MercadoLibreListing
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_publisher_impl.close_publication_service import MercadoLibreClosePublicationService

logger = logging.getLogger(__name__)

CLASSIFICATION_GTIN = "gtin"
CLASSIFICATION_PRICE = "price"
CLASSIFICATION_OTHER = "other"

GTIN_ERROR_SUBSTRINGS = (
    "item.attribute.product_identifier.invalid_format",
    "item.attribute.invalid_product_identifier",
)
GTIN_CONDITIONAL_SUBSTRING = "item.attribute.missing_conditional_required"
PRICE_ERROR_SUBSTRING = "item.price.invalid"


def classify_sync_error(sync_error: Optional[str]) -> str:
    """Return one of CLASSIFICATION_GTIN / CLASSIFICATION_PRICE / CLASSIFICATION_OTHER."""
    text = sync_error or ""
    if any(marker in text for marker in GTIN_ERROR_SUBSTRINGS):
        return CLASSIFICATION_GTIN
    if GTIN_CONDITIONAL_SUBSTRING in text and ("GTIN" in text or "gtin" in text):
        return CLASSIFICATION_GTIN
    if PRICE_ERROR_SUBSTRING in text:
        return CLASSIFICATION_PRICE
    return CLASSIFICATION_OTHER


class MercadoLibreErrorRemediationService:
    def __init__(self, ml_client: MercadoLibreClient) -> None:
        self._close_service = MercadoLibreClosePublicationService(ml_client=ml_client)

    def remediate_all(self, limit: Optional[int] = None, dry_run: bool = False) -> dict[str, int]:
        """Iterate ERROR listings and apply remediation. Returns counts per classification."""
        stats: dict[str, int] = {
            CLASSIFICATION_GTIN: 0,
            CLASSIFICATION_PRICE: 0,
            CLASSIFICATION_OTHER: 0,
            "failed": 0,
            "total": 0,
        }

        qs = MercadoLibreListing.objects.filter(
            status=MercadoLibreListing.Status.ERROR,
            sync_error__isnull=False,
        ).select_related("product_master")

        if limit:
            qs = qs[:limit]

        for listing in qs:
            stats["total"] += 1
            classification = classify_sync_error(listing.sync_error)
            try:
                self._remediate_one(listing, classification, dry_run=dry_run)
                stats[classification] += 1
            except Exception:
                logger.exception("Failed to remediate listing %s", listing.pk)
                stats["failed"] += 1

        logger.info("Remediation finished: %s", stats)
        return stats

    def _remediate_one(self, listing: MercadoLibreListing, classification: str, dry_run: bool) -> None:
        product = listing.product_master

        if classification == CLASSIFICATION_GTIN:
            if dry_run:
                logger.info("Dry run: would clear GTIN on product %s and delete listing %s.", product.code, listing.pk)
                return
            if product.gtin or product.gtin_source:
                product.gtin = None
                product.gtin_source = None
                product.save(update_fields=["gtin", "gtin_source"])
            self._delete_listing(listing)
            return

        if classification == CLASSIFICATION_PRICE:
            if dry_run:
                logger.info("Dry run: would delete price-failed listing %s.", listing.pk)
                return
            self._delete_listing(listing)
            return

        # CLASSIFICATION_OTHER
        if dry_run:
            logger.info("Dry run: would delete other-error listing %s (%s).", listing.pk, (listing.sync_error or "")[:120])
            return
        self._delete_listing(listing)

    def _delete_listing(self, listing: MercadoLibreListing) -> None:
        """Close on ML (if it has an ml_id) and delete the local row."""
        if listing.ml_id:
            # close_listing closes on ML and deletes the local row.
            if self._close_service.close_listing(listing, dry_run=False):
                return
            logger.warning("Closing listing %s failed; deleting local row anyway.", listing.pk)
        listing.delete()
