import logging
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class StorageGateway:
    """Handles image storage operations, specifically AWS S3."""

    def __init__(self, s3_client=None, bucket_name: str | None = None, region_name: str | None = None):
        """Initialize the storage gateway with S3 configuration.

        Args:
            s3_client: Optional boto3 S3 client instance.
            bucket_name: Name of the S3 bucket.
            region_name: AWS region for the S3 bucket.
        """
        self.s3_client = s3_client or boto3.client("s3")
        self.bucket_name = bucket_name
        self.region_name = region_name

    def upload(self, image_bytes: bytes, product_code: str, image_name: str) -> str | None:
        """Upload an image to S3 and return the public URL.

        Args:
            image_bytes: The image data as bytes.
            product_code: The product code for the image path.
            image_name: The name of the image file.

        Returns:
            The public S3 URL if successful, None otherwise.
        """
        if not self.bucket_name:
            logger.error("Bucket name not configured for StorageGateway.")
            return None

        logger.info(f"Uploading {image_name} for product {product_code} to S3.")
        try:
            s3_key = f"products/{product_code}/{image_name}.jpg"

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
            logger.error(f"Error uploading image {image_name} for product {product_code} to S3: {e}")
            return None
