from __future__ import annotations

import logging

import boto3
from django.conf import settings

from aiecommerce.models.product import ProductMaster
from aiecommerce.tasks.upscale_images import process_highres_image_task

logger = logging.getLogger(__name__)


def _delete_s3_objects_for_product(product_code: str) -> int:
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    if not bucket:
        logger.warning("AWS_STORAGE_BUCKET_NAME not configured; skipping S3 cleanup for %s", product_code)
        return 0

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    prefix = f"products/{product_code}/"
    paginator = s3_client.get_paginator("list_objects_v2")
    deleted = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents") or []
        if not contents:
            continue

        for i in range(0, len(contents), 1000):
            batch = contents[i : i + 1000]
            response = s3_client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in batch]},
            )
            deleted += len(response.get("Deleted") or [])
            for err in response.get("Errors") or []:
                logger.error("Failed to delete S3 key %s: %s", err.get("Key"), err.get("Message"))

    logger.info("Deleted %d S3 object(s) under prefix %s", deleted, prefix)
    return deleted


def refresh_product_images(product_code: str) -> str:
    """Delete existing images (DB + S3) and enqueue a fresh upscale task.

    Returns the Celery task id so callers can surface it to operators.
    """
    product = ProductMaster.objects.get(code=product_code)

    _delete_s3_objects_for_product(product.code)

    deleted_count, _ = product.images.all().delete()
    logger.info("Deleted %d ProductImage row(s) for product %s", deleted_count, product.code)

    async_result = process_highres_image_task.delay(product.code)
    logger.info("Enqueued process_highres_image_task %s for product %s", async_result.id, product.code)
    return async_result.id
