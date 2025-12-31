"""Celery tasks for image processing."""

import logging

from celery import shared_task
from django.db import transaction

from aiecommerce.models import MercadoLibreListing, ProductImage, ProductMaster
from aiecommerce.services.image_processor import ImageProcessorService
from aiecommerce.services.mercadolibre_impl.image_search import ImageSearchService

logger = logging.getLogger(__name__)


@shared_task
def process_product_image(product_id: int) -> None:
    """
    Fetches a product, finds up to 5 images, processes them, and saves them.

    Workflow:
    1.  Fetch the ProductMaster record.
    2.  Use ImageSearchService to find up to 5 image URLs.
    3.  Loop through the results:
        - Download the image.
        - Process the image (resize, center, etc.). Remove background only for the first one.
        - Upload to S3.
    4.  Create a ProductImage record for each successfully uploaded image.
    5.  If no images are processed, update the MercadoLibreListing status to 'ERROR'.
    """
    try:
        product = ProductMaster.objects.get(pk=product_id)
        logger.info(f"Processing images for product: {product.description}")
    except ProductMaster.DoesNotExist:
        logger.error(f"ProductMaster with id {product_id} not found.")
        return

    image_search_service = ImageSearchService()
    image_processor_service = ImageProcessorService()

    search_query = image_search_service.build_search_query(product)
    image_urls = image_search_service.find_image_urls(search_query, count=5)

    if not image_urls:
        logger.warning(f"Image search failed for product {product.id}: No results found.")
        with transaction.atomic():
            listing, _ = MercadoLibreListing.objects.update_or_create(
                product_master=product,
                defaults={
                    "status": "ERROR",
                    "sync_error": "Image search failed: No results found",
                },
            )
            logger.info(f"Updated MercadoLibreListing {listing.id} to ERROR state.")
        return

    logger.info(f"Found {len(image_urls)} images for product {product.id}.")

    processed_images = []
    for i, image_url in enumerate(image_urls):
        image_bytes = image_processor_service.download_image(image_url)
        if not image_bytes:
            continue

        # For the first image, remove the background. All images are processed.
        processed_image_bytes = image_processor_service.process_image(image_bytes, with_background_removal=(i == 0))

        if not processed_image_bytes:
            continue

        # Use a generic name for the image, as we don't have one from the search
        image_name = f"image_{i + 1}"
        s3_url = image_processor_service.upload_to_s3(processed_image_bytes, product.id, image_name)

        if s3_url:
            product_image = ProductImage(product=product, url=s3_url, order=i, is_processed=True)
            processed_images.append(product_image)

    if processed_images:
        with transaction.atomic():
            ProductImage.objects.bulk_create(processed_images)
            logger.info(f"Successfully created {len(processed_images)} ProductImage records for product {product.id}.")
    else:
        logger.warning(f"Image processing failed for product {product.id}: No images could be processed.")
        with transaction.atomic():
            listing, _ = MercadoLibreListing.objects.update_or_create(
                product_master=product,
                defaults={
                    "status": "ERROR",
                    "sync_error": "Image processing failed: No images were downloaded or uploaded",
                },
            )
            logger.info(f"Updated MercadoLibreListing {listing.id} to ERROR state because no images were processed.")
