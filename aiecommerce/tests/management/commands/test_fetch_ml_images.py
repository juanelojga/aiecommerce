from unittest.mock import patch

import pytest
from django.core.management import call_command
from model_bakery import baker

from aiecommerce.models import ProductMaster


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images_dry_run(mock_process_product_image, capsys):
    baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        description="Product 1",
    )
    baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
        description="Product 2",
    )

    call_command("fetch_ml_images", "--dry-run")

    captured = capsys.readouterr()
    assert "Found 2 products that would have images fetched" in captured.out
    assert "- Product 1" in captured.out
    assert "- Product 2" in captured.out
    mock_process_product_image.delay.assert_not_called()


@pytest.mark.django_db
@patch("aiecommerce.management.commands.fetch_ml_images.process_product_image")
def test_fetch_ml_images(mock_process_product_image, capsys):
    product1 = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
    )
    product2 = baker.make(
        ProductMaster,
        is_active=True,
        is_for_mercadolibre=True,
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
        _quantity=5,
    )

    call_command("fetch_ml_images", "--limit=2")

    captured = capsys.readouterr()
    assert "Found 2 products to process. Triggering Celery tasks..." in captured.out
    assert mock_process_product_image.delay.call_count == 2
