"""Celery tasks for image processing."""

import logging

from celery import shared_task
from django.db import transaction

from aiecommerce.models import MercadoLibreListing, ProductMaster
from aiecommerce.services.mercadolibre_impl.image_search import ImageSearchService

logger = logging.getLogger(__name__)


@shared_task
def process_product_image(product_id: int) -> None:
    """
    Fetches a product, finds an image, and prepares it for listing.

    Workflow:
    1. Fetch the ProductMaster record.
    2. Use ImageSearchService to find an image URL.
    3. If an image is found, log it and proceed.
    4. If no image is found, update the corresponding MercadoLibreListing
       to an ERROR state with a descriptive message.
    """
    try:
        product = ProductMaster.objects.get(pk=product_id)
        logger.info(f"Processing image for product: {product.description}")
    except ProductMaster.DoesNotExist:
        logger.error(f"ProductMaster with id {product_id} not found.")
        return

    image_search_service = ImageSearchService()
    search_query = image_search_service.build_search_query(product)
    image_urls = image_search_service.find_image_urls(search_query)
    image_url = image_urls[0] if image_urls else None

    if not image_url:
        logger.warning(f"Image search failed for product {product.id}: No results found.")
        with transaction.atomic():
            listing, _ = MercadoLibreListing.objects.update_or_create(
                product=product,
                defaults={
                    "status": "ERROR",
                    "sync_error": "Image search failed: No results found",
                },
            )
            logger.info(f"Updated MercadoLibreListing {listing.id} to ERROR state.")
        return

    logger.info(f"Image found for product {product.id}: {image_url}. Proceeding to background removal (placeholder).")
    # Placeholder for the next step, e.g., calling another task
    # remove_background.delay(product_id, image_url)
