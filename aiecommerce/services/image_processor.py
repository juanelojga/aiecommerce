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

    def _is_dark_background(self, img: Image.Image, threshold: int = 45) -> bool:
        """
        Detects if the image background is black or dark by sampling the edges.
        Luminance threshold: 0 (black) to 255 (white). 45 is a safe dark-gray limit.
        """
        # Convert to grayscale to analyze luminance
        gray_img = img.convert("L")
        width, height = gray_img.size

        # Sample points at the edges and corners where background is expected
        samples = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
            (width // 2, 0),
            (width // 2, height - 1),
            (0, height // 2),
            (width - 1, height // 2),
        ]

        pixel_values = [gray_img.getpixel(pos) for pos in samples]
        avg_luminance = sum(pixel_values) / len(pixel_values)

        return avg_luminance < threshold

    def process_image(self, image_bytes: bytes, with_background_removal: bool = False) -> bytes | None:
        """
        Processes an image. Ignores images with dark or black backgrounds.
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # 1. Background Check: Ignore if dark or black
                if self._is_dark_background(img):
                    logger.info("Image detected with dark/black background. Ignoring as per preference.")
                    return None

                img = img.convert("RGBA")

                if with_background_removal:
                    # 2. Background removal using the shared session
                    processed_bytes = remove(image_bytes, session=self.session)
                    img = Image.open(BytesIO(processed_bytes)).convert("RGBA")

                    # 3. AUTO-CROP: Remove excess transparency to focus on the product
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                # 4. Create standardized 800x800 White Canvas (Mercado Libre Standard)
                canvas_size = (800, 800)
                canvas = Image.new("RGB", canvas_size, (255, 255, 255))

                # Resize to fit within 760x760 (leaving a 20px padding margin)
                img.thumbnail((760, 760), Image.Resampling.LANCZOS)

                # Center the product
                paste_x = (canvas_size[0] - img.width) // 2
                paste_y = (canvas_size[1] - img.height) // 2

                # 5. Final Paste using the product as the alpha mask
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
