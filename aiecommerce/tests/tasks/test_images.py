"""Tests for image processing tasks."""

import logging
from unittest.mock import call, patch

import pytest
from model_bakery import baker

from aiecommerce.models import ProductImage, ProductMaster
from aiecommerce.tasks.images import process_product_image

pytestmark = pytest.mark.django_db


@patch("aiecommerce.tasks.images.ImageProcessorService")
@patch("aiecommerce.tasks.images.ImageSearchService")
def test_process_product_image_success(mock_image_search_service, mock_image_processor_service, caplog):
    """
    Verify that process_product_image successfully processes multiple images,
    with special handling for the first one.
    """
    # Arrange
    caplog.set_level(logging.INFO)
    product = baker.make(ProductMaster, code="PROD001")
    fake_urls = [f"http://example.com/image-{i}.jpg" for i in range(5)]
    raw_image_data = b"raw_image_data"

    mock_search_instance = mock_image_search_service.return_value
    mock_search_instance.build_search_query.return_value = "a search query"
    mock_search_instance.find_image_urls.return_value = fake_urls

    mock_processor_instance = mock_image_processor_service.return_value
    mock_processor_instance.is_duplicate.return_value = False
    mock_processor_instance.download_image.return_value = raw_image_data
    mock_processor_instance.process_image.return_value = b"processed_image_data"
    mock_processor_instance.upload_to_s3.side_effect = lambda _, __, image_name: f"http://s3.com/{image_name}.jpg"

    # Act
    process_product_image(product.id)

    # Assert
    assert ProductImage.objects.filter(product=product).count() == 5

    first_image = ProductImage.objects.get(product=product, order=0)
    assert first_image.is_processed
    assert first_image.url == "http://s3.com/image_1.jpg"

    # Verify that process_image was called correctly
    assert mock_processor_instance.process_image.call_count == 5
    mock_processor_instance.process_image.assert_has_calls(
        [
            call(raw_image_data, with_background_removal=True),
            call(raw_image_data, with_background_removal=False),
            call(raw_image_data, with_background_removal=False),
            call(raw_image_data, with_background_removal=False),
            call(raw_image_data, with_background_removal=False),
        ]
    )

    assert mock_processor_instance.download_image.call_count == 5
    assert mock_processor_instance.upload_to_s3.call_count == 5

    assert f"Successfully created 5 ProductImage records for product {product.id}" in caplog.text


@patch("aiecommerce.tasks.images.ImageSearchService")
def test_process_product_image_no_images_found(mock_image_search_service, caplog):
    """
    Verify that a warning is logged if the image search returns no results.
    """
    # Arrange
    caplog.set_level(logging.INFO)
    product = baker.make(ProductMaster, code="PROD003")

    mock_search_instance = mock_image_search_service.return_value
    mock_search_instance.build_search_query.return_value = "a search query"
    mock_search_instance.find_image_urls.return_value = []

    # Act
    process_product_image(product.id)

    # Assert
    assert ProductImage.objects.count() == 0
    assert f"Image processing failed for product {product.id}: No images could be processed." in caplog.text


@patch("aiecommerce.tasks.images.ImageProcessorService")
@patch("aiecommerce.tasks.images.ImageSearchService")
def test_process_product_image_download_fails(mock_image_search_service, mock_image_processor_service):
    """
    Verify that a failure to download an image is handled gracefully
    and does not stop the processing of other images.
    """
    # Arrange
    product = baker.make(ProductMaster, code="PROD002")
    fake_urls = [f"http://example.com/image-{i}.jpg" for i in range(3)]

    mock_search_instance = mock_image_search_service.return_value
    mock_search_instance.find_image_urls.return_value = fake_urls

    mock_processor_instance = mock_image_processor_service.return_value
    mock_processor_instance.is_duplicate.return_value = False
    # Fail the download for the second image
    mock_processor_instance.download_image.side_effect = [
        b"image_data_1",
        None,
        b"image_data_3",
    ]
    mock_processor_instance.process_image.return_value = b"processed_image_data"
    mock_processor_instance.upload_to_s3.side_effect = lambda _, __, image_name: f"http://s3.com/{image_name}.jpg"

    # Act
    process_product_image(product.id)

    # Assert
    assert ProductImage.objects.filter(product=product).count() == 2
    assert not ProductImage.objects.filter(product=product, order=1).exists()
    assert mock_processor_instance.download_image.call_count == 3
    # Process and upload should only be called for successful downloads
    assert mock_processor_instance.process_image.call_count == 2
    assert mock_processor_instance.upload_to_s3.call_count == 2
