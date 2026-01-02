"""A service for processing images."""

import logging
from io import BytesIO

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from PIL import Image
from rembg import new_session, remove
from requests import RequestException

logger = logging.getLogger(__name__)


class ImageProcessorService:
    """A service for processing images."""

    def __init__(self):
        # Initialize a session for better consistency in removal
        self.session = new_session()

    def download_image(self, url: str) -> bytes | None:
        """Downloads an image from a URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except RequestException as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None

    def remove_background(self, image_bytes: bytes) -> bytes | None:
        """
        Removes the background from an image and processes it.

        This method is a convenience wrapper around `process_image` with background removal enabled.
        """
        return self.process_image(image_bytes, with_background_removal=True)

    def process_image(self, image_bytes: bytes, with_background_removal: bool = False) -> bytes | None:
        """Processes images with Auto-Crop to handle vertical/narrow products like Micro PCs."""
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                img = img.convert("RGBA")

                if with_background_removal:
                    # 1. Background removal
                    processed_bytes = remove(image_bytes, session=self.session)
                    img = Image.open(BytesIO(processed_bytes)).convert("RGBA")

                    # 2. AUTO-CROP: Trim all transparent/white pixels to find the real product bounds
                    # This ensures the product 'fills' the 800x800 canvas correctly.
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                # 3. Standardize to 800x800 White Canvas
                canvas_size = (800, 800)
                canvas = Image.new("RGB", canvas_size, (255, 255, 255))

                # Resize to fit (max 760 to leave a small 20px margin)
                img.thumbnail((760, 760), Image.Resampling.LANCZOS)

                # Center on canvas
                paste_x = (canvas_size[0] - img.width) // 2
                paste_y = (canvas_size[1] - img.height) // 2

                # 4. Paste with mask to preserve colors
                canvas.paste(img, (paste_x, paste_y), mask=img)

                output_buffer = BytesIO()
                canvas.save(output_buffer, format="JPEG", quality=95, subsampling=0)
                return output_buffer.getvalue()
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None

    def upload_to_s3(self, image_bytes: bytes, product_id: int, image_name: str) -> str | None:
        """Uploads an image to S3 and returns the public URL."""
        logger.info(f"Uploading {image_name} for product {product_id} to S3.")
        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            s3_key = f"products/{product_id}/{image_name}.jpg"

            # REMOVED "ACL": "public-read" from ExtraArgs
            s3_client.upload_fileobj(
                BytesIO(image_bytes),
                bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            s3_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded to {s3_url}")
            return s3_url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error uploading image {image_name} for product {product_id} to S3: {e}")
            return None
