"""A service for processing images."""

import logging
from io import BytesIO

import boto3
import numpy as np
import requests
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from PIL import Image, ImageOps
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
        """Processes an image using Hybrid Thresholding to prevent product erasure."""
        logger.info(f"Processing image. Background removal: {with_background_removal}")
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                img = img.convert("RGBA")
                original_img = img.copy()

                if with_background_removal:
                    # 1. Try automated removal with alpha matting for better edges
                    processed_bytes = remove(image_bytes, alpha_matting=True)
                    processed_img = Image.open(BytesIO(processed_bytes)).convert("RGBA")

                    # 2. ANTI-ERASURE CHECK:
                    # If the center of the image became transparent, the AI failed.
                    # We check the alpha channel of the central 50% of the image.
                    w, h = processed_img.size
                    center_box = (w // 4, h // 4, 3 * w // 4, 3 * h // 4)
                    center_alpha = processed_img.getchannel("A").crop(center_box)

                    # If mean alpha in the center is low (< 100), the product was erased.
                    if np.mean(np.array(center_alpha)) < 100:
                        logger.warning("AI erased product. Switching to Color-Safe Thresholding.")
                        # Use a luminance mask to keep anything that isn't white (dark PC)
                        grayscale = ImageOps.grayscale(original_img.convert("RGB"))
                        # Threshold: keep pixels darker than 245 (0=black, 255=white)
                        mask = grayscale.point(lambda p: 255 if p < 245 else 0).convert("L")
                        img_to_use = original_img.copy()
                        img_to_use.putalpha(mask)
                    else:
                        img_to_use = processed_img
                else:
                    img_to_use = original_img

                # 3. Create standardized 800x800 White Canvas
                canvas_size = (800, 800)
                canvas = Image.new("RGB", canvas_size, (255, 255, 255))

                # Resize product (thumbnail preserves aspect ratio)
                img_to_use.thumbnail(canvas_size, Image.Resampling.LANCZOS)

                # Center the product
                paste_x = (canvas_size[0] - img_to_use.width) // 2
                paste_y = (canvas_size[1] - img_to_use.height) // 2

                # 4. Paste using the mask to ensure the product body is OPAQUE
                canvas.paste(img_to_use, (paste_x, paste_y), mask=img_to_use)

                output_buffer = BytesIO()
                # Save as JPEG with maximum quality and no color subsampling
                canvas.save(output_buffer, format="JPEG", quality=100, subsampling=0)
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
