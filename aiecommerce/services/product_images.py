from __future__ import annotations

import logging

import boto3
from celery import Signature
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


def delete_product_image_artifacts(product_code: str) -> None:
    """Delete a product's stored images from S3 and the ProductImage table.

    Raises ProductMaster.DoesNotExist if the product code is unknown.
    """
    product = ProductMaster.objects.get(code=product_code)
    code = product.code or product_code

    _delete_s3_objects_for_product(code)

    deleted_count, _ = product.images.all().delete()
    logger.info("Deleted %d ProductImage row(s) for product %s", deleted_count, code)


def refresh_product_images(product_code: str, link: Signature | None = None) -> str:
    """Delete existing images (DB + S3) and enqueue a fresh upscale task.

    Pass a Celery signature as *link* to chain work after the image task completes.
    Returns the Celery task id so callers can surface it to operators.
    """
    delete_product_image_artifacts(product_code)

    if link is not None:
        async_result = process_highres_image_task.apply_async(args=(product_code,), link=link)
    else:
        async_result = process_highres_image_task.delay(product_code)
    logger.info("Enqueued process_highres_image_task %s for product %s", async_result.id, product_code)
    return async_result.id
