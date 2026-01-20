"""Tests for the upscale_images Celery task."""

import logging
from unittest.mock import patch

import pytest
from model_bakery import baker

from aiecommerce.models.product import ProductDetailScrape, ProductImage, ProductMaster
from aiecommerce.tasks.upscale_images import process_highres_image_task

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_downloader():
    with patch("aiecommerce.tasks.upscale_images.ImageDownloader") as mock:
        yield mock.return_value


@pytest.fixture
def mock_transformer():
    with patch("aiecommerce.tasks.upscale_images.HighResImageTransformer") as mock:
        yield mock.return_value


@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock:
        yield mock


@pytest.fixture
def mock_storage_gateway():
    with patch("aiecommerce.tasks.upscale_images.StorageGateway") as mock:
        yield mock.return_value


def test_process_highres_image_task_success(mock_downloader, mock_transformer, mock_storage_gateway, mock_boto3_client, caplog):
    """
    Test that the task successfully processes images for a product.
    """
    caplog.set_level(logging.INFO)
    product = baker.make(ProductMaster, code="TEST-PROD-1")
    image_urls = [
        "https://example.com/sm/image1-sm.jpg",
        "https://example.com/sm/image2-sm.jpg",
    ]
    baker.make(ProductDetailScrape, product=product, image_urls=image_urls)

    mock_downloader.download.return_value = b"original_bytes"
    mock_transformer.transform.return_value = b"processed_bytes"
    mock_storage_gateway.upload.side_effect = lambda bytes, code, name: f"https://s3.amazonaws.com/{code}/{name}.jpg"

    process_highres_image_task("TEST-PROD-1")

    # Verify calls
    assert mock_downloader.download.call_count == 2
    # Check that URLs were transformed from sm to lg
    mock_downloader.download.assert_any_call("https://example.com/lg/image1-lg.jpg")
    mock_downloader.download.assert_any_call("https://example.com/lg/image2-lg.jpg")

    assert mock_transformer.transform.call_count == 2
    assert mock_storage_gateway.upload.call_count == 2

    # Verify database records
    product_images = ProductImage.objects.filter(product=product).order_by("order")
    assert product_images.count() == 2
    assert product_images[0].url == "https://s3.amazonaws.com/TEST-PROD-1/tecnomega-image_1.jpg"
    assert product_images[0].order == 0
    assert product_images[0].is_processed is True
    assert product_images[1].url == "https://s3.amazonaws.com/TEST-PROD-1/tecnomega-image_2.jpg"
    assert product_images[1].order == 1

    assert "Successfully processed and saved image" in caplog.text
    assert "Finished high-resolution image processing for product: TEST-PROD-1" in caplog.text


def test_process_highres_image_task_product_not_found(caplog):
    """
    Test that the task handles cases where the product does not exist.
    """
    caplog.set_level(logging.ERROR)
    process_highres_image_task("NON-EXISTENT")
    assert "Product with ID NON-EXISTENT not found." in caplog.text


def test_process_highres_image_task_no_scrape_found(caplog):
    """
    Test that the task handles cases where no detail scrape is found for the product.
    """
    caplog.set_level(logging.WARNING)
    baker.make(ProductMaster, code="NO-SCRAPE")
    process_highres_image_task("NO-SCRAPE")
    assert "No detail scrape found for product (ID: NO-SCRAPE)." in caplog.text


def test_process_highres_image_task_no_image_urls(caplog):
    """
    Test that the task handles cases where the scrape has no image URLs.
    """
    caplog.set_level(logging.INFO)
    product = baker.make(ProductMaster, code="NO-IMAGES")
    baker.make(ProductDetailScrape, product=product, image_urls=[])

    process_highres_image_task("NO-IMAGES")
    assert "No image URLs found for product (ID: NO-IMAGES)." in caplog.text


def test_process_highres_image_task_download_fails(mock_downloader, mock_transformer, mock_storage_gateway, mock_boto3_client, caplog):
    """
    Test that the task continues processing other images if one fails to download.
    """
    caplog.set_level(logging.WARNING)
    product = baker.make(ProductMaster, code="DL-FAIL")
    image_urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
    baker.make(ProductDetailScrape, product=product, image_urls=image_urls)

    # Fail the first download, succeed in the second
    mock_downloader.download.side_effect = [None, b"image2_bytes"]
    mock_transformer.transform.return_value = b"processed_bytes"
    mock_storage_gateway.upload.return_value = "https://s3.com/img2.jpg"

    process_highres_image_task("DL-FAIL")

    assert mock_downloader.download.call_count == 2
    assert "Failed to download image from URL: https://example.com/img1.jpg" in caplog.text
    assert ProductImage.objects.filter(product=product).count() == 1
    assert ProductImage.objects.get(product=product).order == 1


def test_process_highres_image_task_transform_fails(mock_downloader, mock_transformer, mock_storage_gateway, mock_boto3_client, caplog):
    """
    Test that the task continues processing other images if one fails to transform.
    """
    caplog.set_level(logging.WARNING)
    product = baker.make(ProductMaster, code="TRANS-FAIL")
    image_urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
    baker.make(ProductDetailScrape, product=product, image_urls=image_urls)

    mock_downloader.download.return_value = b"image_bytes"
    # Fail the first transform, succeed in the second
    mock_transformer.transform.side_effect = [None, b"processed_bytes"]
    mock_storage_gateway.upload.return_value = "https://s3.com/img2.jpg"

    process_highres_image_task("TRANS-FAIL")

    assert mock_transformer.transform.call_count == 2
    assert "Failed to transform image from URL: https://example.com/img1.jpg" in caplog.text
    assert ProductImage.objects.filter(product=product).count() == 1


def test_process_highres_image_task_upload_fails(mock_downloader, mock_transformer, mock_storage_gateway, mock_boto3_client, caplog):
    """
    Test that the task continues processing other images if one fails to upload.
    """
    caplog.set_level(logging.ERROR)
    product = baker.make(ProductMaster, code="UP-FAIL")
    image_urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
    baker.make(ProductDetailScrape, product=product, image_urls=image_urls)

    mock_downloader.download.return_value = b"image_bytes"
    mock_transformer.transform.return_value = b"processed_bytes"
    # Fail the first upload, succeed in the second
    mock_storage_gateway.upload.side_effect = [None, "https://s3.com/img2.jpg"]

    process_highres_image_task("UP-FAIL")

    assert mock_storage_gateway.upload.call_count == 2
    assert "Failed to upload processed image to S3 for URL: https://example.com/img1.jpg" in caplog.text
    assert ProductImage.objects.filter(product=product).count() == 1


def test_process_highres_image_task_unexpected_exception(mock_downloader, mock_transformer, mock_storage_gateway, mock_boto3_client, caplog):
    """
    Test that the task handles an unexpected exception during the image processing loop.
    """
    caplog.set_level(logging.ERROR)
    product = baker.make(ProductMaster, code="EXCEPTION")
    image_urls = ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
    baker.make(ProductDetailScrape, product=product, image_urls=image_urls)

    mock_downloader.download.side_effect = [Exception("Unexpected error"), b"image2_bytes"]
    mock_transformer.transform.return_value = b"processed_bytes"
    mock_storage_gateway.upload.return_value = "https://s3.com/img2.jpg"

    process_highres_image_task("EXCEPTION")

    assert "An unexpected error occurred while processing image URL https://example.com/img1.jpg: Unexpected error" in caplog.text
    assert ProductImage.objects.filter(product=product).count() == 1
