"""A service for processing images."""

import logging
from io import BytesIO

import boto3
import requests
from django.conf import settings
from PIL import Image
from rembg import remove
from requests import RequestException

logger = logging.getLogger(__name__)


class ImageProcessorService:
    """A service for processing images."""

    def download_image(self, url: str) -> bytes | None:
        """Downloads an image from a URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except RequestException as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None

    def _resize_image(self, image_bytes: bytes) -> bytes:
        """Resizes an image to 800x800 pixels."""
        try:
            with Image.open(BytesIO(image_bytes)) as img_obj:
                img_obj = img_obj.resize((800, 800), Image.Resampling.LANCZOS)
                output_buffer = BytesIO()
                img_obj.save(output_buffer, format="JPEG")
                return output_buffer.getvalue()
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            raise

    def remove_background(self, image_bytes: bytes) -> bytes:
        """
        Removes the background from an image using rembg, pads the alpha channel to white,
        converts to RGB, and resizes to 800x800.
        """
        logger.info("Removing background from image.")
        try:
            # Use rembg to remove the background
            image_without_bg_bytes = remove(image_bytes)

            # Open the image with Pillow
            with Image.open(BytesIO(image_without_bg_bytes)) as img:
                # Create a new image with a white background
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    alpha = img.convert("RGBA").split()[-1]
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=alpha)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Convert to bytes for resizing
                output_buffer = BytesIO()
                img.save(output_buffer, format="JPEG")
                processed_image_bytes = output_buffer.getvalue()

            # Resize the image
            return self._resize_image(processed_image_bytes)
        except Exception as e:
            logger.error(f"Error removing background from image: {e}")
            raise

    def upload_to_s3(self, image_bytes: bytes, product_id: int, image_name: str) -> str:
        """Uploads an image to S3."""
        logger.info(f"Uploading {image_name} for product {product_id} to S3.")
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            s3_key = f"{product_id}/{image_name}.jpg"

            s3.upload_fileobj(
                BytesIO(image_bytes),
                bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "image/jpeg", "ACL": "public-read"},
            )
            s3_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            return s3_url
        except Exception as e:
            logger.error(f"Error uploading image {image_name} for product {product_id} to S3: {e}")
            raise
