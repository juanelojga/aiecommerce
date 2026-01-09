from unittest.mock import patch

import pytest
from django.core.management import call_command
from model_bakery import baker

from aiecommerce.models import ProductMaster


@pytest.mark.django_db
def test_enrich_products_images_no_products(capsys):
    """Test when no products exist without images."""
    # Create a product with an image
    product = baker.make(ProductMaster, is_active=True)
    baker.make("aiecommerce.ProductImage", product=product)

    call_command("enrich_products_images")

    captured = capsys.readouterr()
    assert "No products found without images." in captured.out


@pytest.mark.django_db
@patch("aiecommerce.management.commands.enrich_products_images.process_product_image")
def test_enrich_products_images_dry_run(mock_process_product_image, capsys):
    """Test dry-run mode."""
    # Create products without images
    p1 = baker.make(ProductMaster, sku="SKU001", description="Desc 1", is_active=True)
    p2 = baker.make(ProductMaster, sku="SKU002", description="Desc 2", is_active=True)

    call_command("enrich_products_images", "--dry-run")

    captured = capsys.readouterr()
    assert "--- DRY RUN MODE: No tasks will be enqueued. ---" in captured.out
    assert f"Would process Product ID: {p1.id}, SKU: {p1.sku}" in captured.out
    assert f"Would process Product ID: {p2.id}, SKU: {p2.sku}" in captured.out

    # Ensure no tasks were enqueued
    mock_process_product_image.delay.assert_not_called()


@pytest.mark.django_db
@patch("aiecommerce.management.commands.enrich_products_images.process_product_image")
@patch("time.sleep", return_value=None)  # Speed up tests
def test_enrich_products_images_normal_run(mock_sleep, mock_process_product_image, capsys):
    """Test normal run enqueuing tasks."""
    p1 = baker.make(ProductMaster, is_active=True)
    p2 = baker.make(ProductMaster, is_active=True)

    # One active with image (should be ignored)
    p3 = baker.make(ProductMaster, is_active=True)
    baker.make("aiecommerce.ProductImage", product=p3)

    # One inactive without image (should be ignored)
    baker.make(ProductMaster, is_active=False)

    call_command("enrich_products_images")

    captured = capsys.readouterr()
    assert f"Successfully enqueued task for Product ID: {p1.id}" in captured.out
    assert f"Successfully enqueued task for Product ID: {p2.id}" in captured.out
    assert "Enqueued 2/2 tasks" in captured.out

    assert mock_process_product_image.delay.call_count == 2
    mock_process_product_image.delay.assert_any_call(p1.id)
    mock_process_product_image.delay.assert_any_call(p2.id)


@pytest.mark.django_db
@patch("aiecommerce.management.commands.enrich_products_images.process_product_image")
@patch("time.sleep", return_value=None)
def test_enrich_products_images_enqueue_failure(mock_sleep, mock_process_product_image, capsys):
    """Test handling of individual task enqueue failure."""
    p1 = baker.make(ProductMaster, is_active=True)

    # Mock delay to raise an exception
    mock_process_product_image.delay.side_effect = Exception("Celery error")

    call_command("enrich_products_images")

    captured = capsys.readouterr()
    assert f"Failed to enqueue task for Product ID: {p1.id}. Error: Celery error" in captured.out
    assert "Enqueued 0/1 tasks" in captured.out
