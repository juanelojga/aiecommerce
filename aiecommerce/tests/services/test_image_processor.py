from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.conf import settings
from PIL import Image

from aiecommerce.services.image_processor import ImageProcessorService


@pytest.fixture
def image_processor_service():
    return ImageProcessorService()


@pytest.fixture
def sample_image_bytes():
    # Create a dummy image
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def transparent_image_bytes():
    # Create a dummy image with transparency: fully transparent image
    img = Image.new("RGBA", (100, 100), color=(0, 0, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageProcessorService:
    @patch("requests.get")
    def test_download_image_success(self, mock_get, image_processor_service, sample_image_bytes):
        mock_response = MagicMock()
        mock_response.content = sample_image_bytes
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "http://example.com/image.png"
        result = image_processor_service.download_image(url)

        assert result == sample_image_bytes
        mock_get.assert_called_once_with(url, timeout=10)

    @patch("requests.get")
    def test_download_image_failure(self, mock_get, image_processor_service):
        mock_get.side_effect = requests.exceptions.RequestException("Download error")

        url = "http://example.com/image.png"
        result = image_processor_service.download_image(url)

        assert result is None
        mock_get.assert_called_once_with(url, timeout=10)

    def test_resize_image(self, image_processor_service, sample_image_bytes):
        resized_image_bytes = image_processor_service._resize_image(sample_image_bytes)
        img = Image.open(BytesIO(resized_image_bytes))
        assert img.size == (800, 800)
        assert img.format == "JPEG"

    @patch("aiecommerce.services.image_processor.remove")
    def test_remove_background(self, mock_rembg_remove, image_processor_service, transparent_image_bytes):
        # Mock rembg.remove to return a transparent image
        mock_rembg_remove.return_value = transparent_image_bytes

        processed_image_bytes = image_processor_service.remove_background(transparent_image_bytes)

        # Verify rembg.remove was called
        mock_rembg_remove.assert_called_once_with(transparent_image_bytes)

        # Open the processed image and verify properties
        img = Image.open(BytesIO(processed_image_bytes))
        assert img.size == (800, 800)
        assert img.format == "JPEG"
        # Check if background is white (by checking a corner pixel, assuming the original was transparent there)
        # This is a simplified check, a more robust test might check multiple pixels or histogram
        assert img.getpixel((0, 0)) == (255, 255, 255)

    @patch("boto3.client")
    def test_upload_to_s3(self, mock_boto_client, image_processor_service, sample_image_bytes):
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Mock settings
        with (
            patch.object(settings, "AWS_ACCESS_KEY_ID", "test_key"),
            patch.object(settings, "AWS_SECRET_ACCESS_KEY", "test_secret"),
            patch.object(settings, "AWS_S3_REGION_NAME", "us-east-1"),
            patch.object(settings, "AWS_STORAGE_BUCKET_NAME", "test-bucket"),
        ):
            product_id = 123
            image_name = "test_image"
            expected_s3_url = f"https://test-bucket.s3.us-east-1.amazonaws.com/{product_id}/{image_name}.jpg"

            result_url = image_processor_service.upload_to_s3(sample_image_bytes, product_id, image_name)

            mock_boto_client.assert_called_once_with(
                "s3",
                aws_access_key_id="test_key",
                aws_secret_access_key="test_secret",
                region_name="us-east-1",
            )
            mock_s3_client.upload_fileobj.assert_called_once()
            args, kwargs = mock_s3_client.upload_fileobj.call_args
            assert args[1] == "test-bucket"
            assert args[2] == f"{product_id}/{image_name}.jpg"
            assert kwargs["ExtraArgs"] == {"ContentType": "image/jpeg", "ACL": "public-read"}
            assert result_url == expected_s3_url
