from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from model_bakery import baker

from aiecommerce.models import ProductMaster


@pytest.fixture
def mock_image_search_service():
    with patch("aiecommerce.management.commands.verify_fetch_product_images.ImageSearchService") as mock_service_class:
        mock_service_instance = MagicMock()
        mock_service_instance.build_search_query.return_value = "Mocked Query"
        mock_service_instance.find_image_urls.return_value = [
            "http://example.com/image1.jpg",
            "http://example.com/image2.jpg",
        ]
        mock_service_class.return_value = mock_service_instance
        yield mock_service_instance


@pytest.mark.django_db
@patch("aiecommerce.management.commands.verify_fetch_product_images.process_product_image")
def test_verify_fetch_product_images_dry_run(mock_process_product_image, mock_image_search_service, capsys):
    product = baker.make(
        ProductMaster,
        code="PROD001",
        is_active=True,
        is_for_mercadolibre=True,
        description="Product 1",
        images=[],  # Explicitly set images to none
    )

    call_command("verify_fetch_product_images", product.code, "--dry-run")

    captured = capsys.readouterr()
    assert "--- DRY RUN MODE ACTIVATED ---" in captured.out
    assert f"- Product: {product.description} (Code: {product.code})" in captured.out
    assert "Query: 'Mocked Query'" in captured.out
    assert "Candidate URLs:" in captured.out
    assert "- http://example.com/image1.jpg" in captured.out
    mock_process_product_image.delay.assert_not_called()
    mock_image_search_service.build_search_query.assert_called_once_with(product)
    mock_image_search_service.find_image_urls.assert_called_once_with("Mocked Query", image_search_count=10)


@pytest.mark.django_db
@patch("aiecommerce.management.commands.verify_fetch_product_images.process_product_image")
def test_verify_fetch_product_images(mock_process_product_image, capsys):
    product = baker.make(
        ProductMaster,
        code="PROD002",
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
    )

    call_command("verify_fetch_product_images", product.code, "--no-dry-run")

    captured = capsys.readouterr()
    assert "Done." in captured.out
    mock_process_product_image.delay.assert_called_once_with(product.id)


@pytest.mark.django_db
def test_verify_fetch_product_images_by_code_not_found(capsys):
    non_existent_code = "NON_EXISTENT"
    with pytest.raises(CommandError) as excinfo:
        call_command("verify_fetch_product_images", non_existent_code)
    assert f"ProductMaster with code '{non_existent_code}' not found." in str(excinfo.value)
