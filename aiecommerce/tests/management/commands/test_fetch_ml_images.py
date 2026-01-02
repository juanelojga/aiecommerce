from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from model_bakery import baker

from aiecommerce.models import ProductMaster


@pytest.fixture
def mock_image_search_service():
    with patch("aiecommerce.management.commands.fetch_ml_images.ImageSearchService") as mock_service_class:
        mock_service_instance = MagicMock()
        mock_service_instance.build_search_query.return_value = "Mocked Query"
        mock_service_instance.find_image_urls.return_value = [
            "http://example.com/image1.jpg",
            "http://example.com/image2.jpg",
        ]
        mock_service_class.return_value = mock_service_instance
        yield mock_service_instance


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images_dry_run(mock_process_product_image, mock_image_search_service, capsys):
    product = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        description="Product 1",
        images=[],  # Explicitly set images to none
    )

    call_command("fetch_ml_images", "--dry-run")

    captured = capsys.readouterr()
    assert "Found 1 products. Performing a dry run" in captured.out
    assert f"- Product: {product.description} (ID: {product.id})" in captured.out
    assert "Query: 'Mocked Query'" in captured.out
    assert "Candidate URLs:" in captured.out
    assert "- http://example.com/image1.jpg" in captured.out
    mock_process_product_image.delay.assert_not_called()
    mock_image_search_service.build_search_query.assert_called_once_with(product)
    mock_image_search_service.find_image_urls.assert_called_once_with("Mocked Query", image_search_count=10)


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images(mock_process_product_image, capsys):
    product1 = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
    )
    product2 = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
    )

    call_command("fetch_ml_images")

    captured = capsys.readouterr()
    assert "Found 2 products to process. Triggering Celery tasks..." in captured.out
    assert mock_process_product_image.delay.call_count == 2
    mock_process_product_image.delay.assert_any_call(product1.id)
    mock_process_product_image.delay.assert_any_call(product2.id)


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images_with_limit(mock_process_product_image, capsys):
    baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
        _quantity=5,
    )

    call_command("fetch_ml_images", "--limit=2")

    captured = capsys.readouterr()
    assert "Found 2 products to process. Triggering Celery tasks..." in captured.out
    assert mock_process_product_image.delay.call_count == 2


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images_by_id(mock_process_product_image, capsys):
    product_to_process = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
    )
    # Another product that should NOT be processed
    baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        images=[],
    )

    call_command("fetch_ml_images", f"--id={product_to_process.id}")

    captured = capsys.readouterr()
    assert f"Processing product with ID {product_to_process.id}" in captured.out
    assert "Found 1 products to process" in captured.out
    mock_process_product_image.delay.assert_called_once_with(product_to_process.id)


@pytest.mark.django_db
def test_fetch_ml_images_by_id_not_found(capsys):
    non_existent_id = 99999
    call_command("fetch_ml_images", f"--id={non_existent_id}")
    captured = capsys.readouterr()
    assert f"Product with ID {non_existent_id} not found" in captured.out
