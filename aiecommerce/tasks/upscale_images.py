from __future__ import annotations

import logging

import boto3
from celery import shared_task
from django.conf import settings
from django.db import transaction

from aiecommerce.models.product import ProductDetailScrape, ProductImage, ProductMaster
from aiecommerce.services.image_processing.downloader import ImageDownloader
from aiecommerce.services.image_processing.storage import StorageGateway
from aiecommerce.services.upscale_images_impl.transformer import HighResImageTransformer

logger = logging.getLogger(__name__)


@shared_task
def process_highres_image_task(product_code: str) -> None:
    """
    Celery task to download, process, and store high-resolution images for a product.

    This task fetches the product's detail scrape, downloads the first 5 images,
    transforms them to a high-resolution format (1200x1200), uploads them to
    cloud storage, and creates associated ProductImage records.
    """
    try:
        product = ProductMaster.objects.get(code=product_code)
        logger.info(f"Starting high-resolution image processing for product: {product.code}")
    except ProductMaster.DoesNotExist:
        logger.error(f"Product with ID {product_code} not found.")
        return

    try:
        scrape = ProductDetailScrape.objects.filter(product=product).latest("created_at")
    except ProductDetailScrape.DoesNotExist:
        logger.warning(f"No detail scrape found for product (ID: {product_code}).")
        return

    image_urls = scrape.image_urls[:5]
    if not image_urls:
        logger.info(f"No image URLs found for product (ID: {product_code}).")
        return

    downloader = ImageDownloader()
    transformer = HighResImageTransformer()

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    storage = StorageGateway(
        s3_client=s3_client,
        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    for i, image_url in enumerate(image_urls):
        image_name = f"tecnomega-image_{i + 1}"

        try:
            image_bytes = downloader.download(image_url)
            if not image_bytes:
                logger.warning(f"Failed to download image from URL: {image_url}")
                continue

            processed_image_bytes = transformer.transform(image_bytes)
            if not processed_image_bytes:
                logger.warning(f"Failed to transform image from URL: {image_url}")
                continue

            s3_url = storage.upload(processed_image_bytes, product_code, image_name)
            if not s3_url:
                logger.error(f"Failed to upload processed image to S3 for URL: {image_url}")
                continue

            with transaction.atomic():
                ProductImage.objects.create(product=product, url=s3_url, is_processed=True, order=i)
            logger.info(f"Successfully processed and saved image from {image_url} to {s3_url}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while processing image URL {image_url}: {e}", exc_info=True)

    logger.info(f"Finished high-resolution image processing for product: {product.code}")
