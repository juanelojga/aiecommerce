"""Celery tasks for image processing."""

import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction

from aiecommerce.models import ProductImage, ProductMaster
from aiecommerce.services.image_processor import ImageProcessorService
from aiecommerce.services.mercadolibre_impl.image_search_service import ImageSearchService

logger = logging.getLogger(__name__)


@shared_task
def process_product_image(product_id_or_code) -> None:
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
    """
    try:
        if str(product_id_or_code).isdigit():
            product = ProductMaster.objects.get(id=int(product_id_or_code))
        else:
            product = ProductMaster.objects.get(code=product_id_or_code)
        logger.info(f"Processing images for product: {product.description}")
    except ProductMaster.DoesNotExist:
        logger.error(f"ProductMaster with ID/code {product_id_or_code} not found.")
        return

    image_search_service = ImageSearchService()
    image_processor_service = ImageProcessorService()
    image_processor_service.clear_session_hashes()

    search_query = image_search_service.build_search_query(product)
    if not search_query:
        logger.error(f"Could not build search query for product {product.id}.")
        return

    image_urls = image_search_service.find_image_urls(search_query, image_search_count=settings.IMAGE_SEARCH_COUNT)

    logger.info(f"Found {len(image_urls)} images for product {product.id}.")

    processed_images = []
    for i, image_url in enumerate(image_urls):
        image_bytes = image_processor_service.download_image(image_url)
        if not image_bytes:
            continue

        # Check for duplicates before processing
        if image_processor_service.is_duplicate(image_bytes):
            continue

        # For the first image, remove the background. All images are processed.
        processed_image_bytes = image_processor_service.process_image(image_bytes, with_background_removal=(i == 0))

        if not processed_image_bytes:
            continue

        # Use a generic name for the image, as we don't have one from the search
        image_name = f"image_{i + 1}"

        if not product.code:
            continue

        s3_url = image_processor_service.upload_to_s3(processed_image_bytes, product.code, image_name)

        if s3_url:
            product_image = ProductImage(product=product, url=s3_url, order=i, is_processed=True)
            processed_images.append(product_image)

    if processed_images:
        with transaction.atomic():
            ProductImage.objects.bulk_create(processed_images)
            logger.info(f"Successfully created {len(processed_images)} ProductImage records for product {product.id}.")
    else:
        logger.warning(f"Image processing failed for product {product.id}: No images could be processed.")
