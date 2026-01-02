from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
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
def another_image_bytes():
    # Create another dummy image with noise
    img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    img = Image.fromarray(img_array, "RGB")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def transparent_image_bytes():
    # Create a dummy image with transparency: fully transparent image
    img = Image.new("RGBA", (200, 300), color=(0, 0, 0, 0))
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

    def test_is_duplicate_new_image(self, image_processor_service, sample_image_bytes):
        """Test that a new image is not marked as a duplicate."""
        is_dup = image_processor_service.is_duplicate(sample_image_bytes)
        assert not is_dup
        assert len(image_processor_service.seen_hashes) == 1

    def test_is_duplicate_same_image(self, image_processor_service, sample_image_bytes):
        """Test that the same image is detected as a duplicate."""
        image_processor_service.is_duplicate(sample_image_bytes)  # First encounter
        is_dup = image_processor_service.is_duplicate(sample_image_bytes)  # Second encounter
        assert is_dup
        assert len(image_processor_service.seen_hashes) == 1

    def test_is_duplicate_different_images(self, image_processor_service, sample_image_bytes, another_image_bytes):
        """Test that different images are not marked as duplicates."""
        image_processor_service.is_duplicate(sample_image_bytes)
        is_dup = image_processor_service.is_duplicate(another_image_bytes)
        assert not is_dup
        assert len(image_processor_service.seen_hashes) == 2

    def test_clear_session_hashes(self, image_processor_service, sample_image_bytes):
        """Test that hashes are cleared."""
        image_processor_service.is_duplicate(sample_image_bytes)
        assert len(image_processor_service.seen_hashes) == 1
        image_processor_service.clear_session_hashes()
        assert len(image_processor_service.seen_hashes) == 0

    @patch("imagehash.phash")
    def test_is_duplicate_hashing_error(self, mock_phash, image_processor_service, sample_image_bytes):
        """Test that if hashing fails, the image is not marked as a duplicate."""
        mock_phash.side_effect = Exception("Hashing failed")
        is_dup = image_processor_service.is_duplicate(sample_image_bytes)
        assert not is_dup
        assert len(image_processor_service.seen_hashes) == 0

    def test_process_image_no_background_removal(self, image_processor_service, sample_image_bytes):
        """Test processing without background removal, ensuring centering and resizing."""
        # Use a non-square image that is definitely NOT dark
        non_square_img = Image.new("RGB", (100, 200), color=(200, 200, 255))
        buffer = BytesIO()
        non_square_img.save(buffer, format="PNG")
        non_square_bytes = buffer.getvalue()

        # Mock Image.open to return a real image so thumbnail works if it's called on a mock
        processed_bytes = image_processor_service.process_image(non_square_bytes, with_background_removal=False)
        assert processed_bytes is not None

        img = Image.open(BytesIO(processed_bytes))
        assert img.size == (800, 800)
        assert img.format == "JPEG"

        # The image (100, 200) will be resized to (380, 760) to fit in (760, 760).
        # The paste position should be ((800-380)/2, (800-760)/2) = (210, 20).
        # Top-left should be white background.
        assert img.getpixel((0, 0)) == (255, 255, 255)
        # A pixel from the image, e.g., center of image (400, 400).
        r, g, b = img.getpixel((400, 400))
        assert b > 240 and r > 190 and g > 190
        # Bottom-right should be white background
        assert img.getpixel((799, 799)) == (255, 255, 255)

    @patch("aiecommerce.services.image_processor.remove")
    def test_process_image_with_background_removal(self, mock_rembg_remove, image_processor_service, transparent_image_bytes):
        mock_rembg_remove.return_value = transparent_image_bytes

        processed_image_bytes = image_processor_service.process_image(transparent_image_bytes, with_background_removal=True)

        mock_rembg_remove.assert_called_once()
        args, kwargs = mock_rembg_remove.call_args
        assert args[0] == transparent_image_bytes
        assert "session" in kwargs

        img = Image.open(BytesIO(processed_image_bytes))
        assert img.size == (800, 800)
        assert img.format == "JPEG"
        # The whole image should be white because the input was transparent
        assert img.getpixel((0, 0)) == (255, 255, 255)
        assert img.getpixel((400, 400)) == (255, 255, 255)

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
            expected_s3_key = f"products/{product_id}/{image_name}.jpg"
            expected_s3_url = f"https://test-bucket.s3.us-east-1.amazonaws.com/{expected_s3_key}"

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
            assert args[2] == expected_s3_key
            assert kwargs["ExtraArgs"] == {"ContentType": "image/jpeg"}
            assert result_url == expected_s3_url

    @patch("aiecommerce.services.image_processor.remove")
    @patch("aiecommerce.services.image_processor.Image.open")
    @patch("aiecommerce.services.image_processor.ImageFilter.MaxFilter")
    @patch("aiecommerce.services.image_processor.Image.new")
    @patch("aiecommerce.services.image_processor.Image.merge")
    def test_process_image_with_bg_removal_features(
        self,
        mock_image_merge,
        mock_image_new,
        mock_max_filter,
        mock_image_open,
        mock_rembg_remove,
        image_processor_service,
        sample_image_bytes,
    ):
        """Test that background removal uses dilation, preserves ICC profile, and logs correctly."""
        # Arrange
        # 1. Mock for original image with ICC profile
        mock_original_img = MagicMock(spec=Image.Image, mode="RGB", info={"icc_profile": b"dummy_profile"})
        mock_original_img.convert.return_value = mock_original_img

        # 2. Mocks for rembg result image and its alpha mask
        mock_rembg_img = MagicMock(spec=Image.Image, mode="RGBA", size=(100, 100))
        mock_rembg_img.width = 100
        mock_rembg_img.height = 100
        mock_r = MagicMock(spec=Image.Image, mode="L", size=(100, 100))
        mock_g = MagicMock(spec=Image.Image, mode="L", size=(100, 100))
        mock_b = MagicMock(spec=Image.Image, mode="L", size=(100, 100))
        mock_alpha = MagicMock(spec=Image.Image, mode="L", size=(100, 100))
        mock_alpha.filter.return_value = mock_alpha  # Make filter return itself to not break the call chain
        mock_rembg_img.split.return_value = (mock_r, mock_g, mock_b, mock_alpha)
        mock_rembg_img.convert.return_value = mock_rembg_img
        mock_rembg_img.getbbox.return_value = (0, 0, 100, 100)
        mock_rembg_img.crop.return_value = mock_rembg_img

        mock_image_merge.return_value = mock_rembg_img

        # Image.open is called twice: once for the original, once for the rembg result
        mock_image_open.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_original_img)),
            MagicMock(__enter__=MagicMock(return_value=mock_rembg_img)),
        ]
        mock_rembg_remove.return_value = b"rembg_bytes"

        # 3. Mocks for canvas creation
        mock_canvas = MagicMock(spec=Image.Image)
        mock_canvas.width = 800
        mock_canvas.height = 800
        # Image.new is called for the white BG and the canvas
        mock_image_new.return_value = mock_canvas

        # Act
        # We need to mock _is_dark_background because it uses getpixel which we haven't mocked for original_img
        with patch.object(image_processor_service, "_is_dark_background", return_value=False):
            image_processor_service.process_image(sample_image_bytes, with_background_removal=True)

        # Assert

        # Assert edge dilation was performed
        mock_max_filter.assert_called_once_with(3)
        mock_alpha.filter.assert_called_once_with(mock_max_filter.return_value)

        # Assert ICC profile was preserved on final save
        mock_canvas.save.assert_called_once()
        _, kwargs = mock_canvas.save.call_args
        assert "icc_profile" in kwargs
        assert kwargs["icc_profile"] == b"dummy_profile"
