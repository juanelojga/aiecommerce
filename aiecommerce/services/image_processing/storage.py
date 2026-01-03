import logging
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class StorageGateway:
    """Handles image storage operations, specifically AWS S3."""

    def __init__(self, s3_client=None, bucket_name: str | None = None, region_name: str | None = None):
        self.s3_client = s3_client or boto3.client("s3")
        self.bucket_name = bucket_name
        self.region_name = region_name

    def upload(self, image_bytes: bytes, product_id: int, image_name: str) -> str | None:
        """Uploads an image to S3 and returns the public URL."""
        if not self.bucket_name:
            logger.error("Bucket name not configured for StorageGateway.")
            return None

        logger.info(f"Uploading {image_name} for product {product_id} to S3.")
        try:
            s3_key = f"products/{product_id}/{image_name}.jpg"

            self.s3_client.upload_fileobj(
                BytesIO(image_bytes),
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

            # Use generate_presigned_url or similar if bucket is not public,
            # but for now we follow the original logic of manual construction.
            # Improved to handle missing region.
            region_part = f".{self.region_name}" if self.region_name else ""
            s3_url = f"https://{self.bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"

            logger.info(f"Successfully uploaded to {s3_url}")
            return s3_url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error uploading image {image_name} for product {product_id} to S3: {e}")
            return None
