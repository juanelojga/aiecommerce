from unittest.mock import patch

import pytest
from django.core.management import call_command

from aiecommerce.tests.factories import ProductDetailScrapeFactory, ProductImageFactory, ProductMasterFactory


@pytest.mark.django_db
def test_upscale_scraped_images_no_products(capsys):
    """Test when no products are found for image upscaling."""
    # Product with image_urls but already processed (should be ignored)
    p = ProductMasterFactory(is_active=True, price=100, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p, image_urls=["http://example.com/img.jpg"])
    ProductImageFactory(product=p, is_processed=True)

    call_command("upscale_scraped_images")

    captured = capsys.readouterr()
    assert "No products found for image upscaling." in captured.out


@pytest.mark.django_db
@patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task.delay")
def test_upscale_scraped_images_dry_run(mock_delay, capsys):
    """Test dry-run mode."""
    p = ProductMasterFactory(is_active=True, price=100, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p, image_urls=["http://example.com/img.jpg"])

    call_command("upscale_scraped_images", "--dry-run")

    captured = capsys.readouterr()
    assert "--- DRY RUN MODE ACTIVATED ---" in captured.out
    assert "Completed. Total candidates: 1" in captured.out
    mock_delay.assert_not_called()


@pytest.mark.django_db
@patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task.delay")
@patch("time.sleep", return_value=None)
def test_upscale_scraped_images_normal_run(mock_sleep, mock_delay, capsys):
    """Test normal run mode."""
    p1 = ProductMasterFactory(code="P1", is_active=True, price=100, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p1, image_urls=["http://example.com/img1.jpg"])

    p2 = ProductMasterFactory(code="P2", is_active=True, price=200, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p2, image_urls=["http://example.com/img2.jpg"])

    call_command("upscale_scraped_images")

    captured = capsys.readouterr()
    assert "Completed. Total candidates: 2" in captured.out
    assert mock_delay.call_count == 2
    mock_delay.assert_any_call("P1")
    mock_delay.assert_any_call("P2")


@pytest.mark.django_db
@patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task.delay")
@patch("time.sleep", return_value=None)
def test_upscale_scraped_images_with_code(mock_sleep, mock_delay, capsys):
    """Test run with a specific product code."""
    p1 = ProductMasterFactory(code="P1", is_active=True, price=100, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p1, image_urls=["http://example.com/img1.jpg"])

    p2 = ProductMasterFactory(code="P2", is_active=True, price=200, category="Test", is_for_mercadolibre=True)
    ProductDetailScrapeFactory(product=p2, image_urls=["http://example.com/img2.jpg"])

    call_command("upscale_scraped_images", "--code=P1")

    captured = capsys.readouterr()
    assert "Completed. Total candidates: 1" in captured.out
    mock_delay.assert_called_once_with("P1")
