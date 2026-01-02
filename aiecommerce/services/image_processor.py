"""A service for processing images."""

import logging
from io import BytesIO

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from PIL import Image, ImageFilter
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

    def remove_background(self, image_bytes: bytes) -> bytes | None:
        """
        Removes the background from an image and processes it.

        This method is a convenience wrapper around `process_image` with background removal enabled.
        """
        return self.process_image(image_bytes, with_background_removal=True)

    def process_image(self, image_bytes: bytes, with_background_removal: bool = False) -> bytes | None:
        """
        Processes an image.

        Optionally removes the background, then centers the image on a pure white
        800x800 pixel canvas, saving it as a high-quality JPEG.
        """
        logger.info(f"Processing image. Background removal: {with_background_removal}")
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                icc_profile = img.info.get("icc_profile")

                processed_img = img
                if with_background_removal:
                    logger.info("Performing color-safe background removal.")
                    # remove() returns RGBA bytes (as a PNG)
                    img_bytes_no_bg = remove(image_bytes)
                    with Image.open(BytesIO(img_bytes_no_bg)) as img_no_bg:
                        # Create a white background
                        bg = Image.new("RGB", img_no_bg.size, (255, 255, 255))
                        # Get the alpha channel as a mask
                        alpha = img_no_bg.split()[-1]
                        # Dilate the mask to smooth edges, preventing clipping.
                        dilated_mask = alpha.filter(ImageFilter.MaxFilter(3))
                        # Paste the image onto the background using the dilated mask
                        bg.paste(img_no_bg, mask=dilated_mask)
                        processed_img = bg
                elif img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    # Handle transparency for non-background-removed images by pasting on a white background.
                    alpha = img.convert("RGBA").split()[-1]
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=alpha)
                    processed_img = bg
                elif img.mode != "RGB":
                    processed_img = img.convert("RGB")

                # Create a white canvas
                canvas_size = (800, 800)
                canvas = Image.new("RGB", canvas_size, (255, 255, 255))

                # Resize image to fit within the canvas while maintaining aspect ratio
                processed_img.thumbnail(canvas_size, Image.Resampling.LANCZOS)

                # Calculate position to center the image
                paste_x = (canvas_size[0] - processed_img.width) // 2
                paste_y = (canvas_size[1] - processed_img.height) // 2

                # Paste the resized image onto the canvas
                canvas.paste(processed_img, (paste_x, paste_y))

                # Save to buffer as high-quality JPEG, preserving color profile
                output_buffer = BytesIO()
                canvas.save(
                    output_buffer,
                    format="JPEG",
                    quality=95,
                    icc_profile=icc_profile,
                )
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
