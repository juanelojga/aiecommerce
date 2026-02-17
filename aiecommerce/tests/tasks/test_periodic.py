from unittest.mock import patch

from aiecommerce.tasks.periodic import (
    run_create_ml_test_user,
    run_enrich_mercadolibre_category,
    run_enrich_products_content,
    run_enrich_products_details,
    run_enrich_products_gtin,
    run_enrich_products_images,
    run_enrich_products_specs,
    run_normalize_products,
    run_prune_scrapes,
    run_publish_ml_product,
    run_scrape_tecnomega,
    run_sync_ml_listings,
    run_sync_price_list,
    run_update_ml_eligibility,
)


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_create_ml_test_user(mock_call_command):
    """Verify that the run_create_ml_test_user task calls the correct management command."""
    run_create_ml_test_user()
    mock_call_command.assert_called_once_with("create_ml_test_user")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_mercadolibre_category(mock_call_command):
    """Verify that the run_enrich_mercadolibre_category task calls the correct management command."""
    run_enrich_mercadolibre_category()
    mock_call_command.assert_called_once_with("enrich_mercadolibre_category")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_products_content(mock_call_command):
    """Verify that the run_enrich_products_content task calls the correct management command."""
    run_enrich_products_content()
    mock_call_command.assert_called_once_with("enrich_products_content")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_products_details(mock_call_command):
    """Verify that the run_enrich_products_details task calls the correct management command."""
    run_enrich_products_details()
    mock_call_command.assert_called_once_with("enrich_products_details")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_products_images(mock_call_command):
    """Verify that the run_enrich_products_images task calls the correct management command."""
    run_enrich_products_images()
    mock_call_command.assert_called_once_with("enrich_products_images")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_products_specs(mock_call_command):
    """Verify that the run_enrich_products_specs task calls the correct management command."""
    run_enrich_products_specs()
    mock_call_command.assert_called_once_with("enrich_products_specs")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_normalize_products(mock_call_command):
    """Verify that the run_normalize_products task calls the correct management command."""
    run_normalize_products()
    mock_call_command.assert_called_once_with("normalize_products")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_prune_scrapes(mock_call_command):
    """Verify that the run_prune_scrapes task calls the correct management command."""
    run_prune_scrapes()
    mock_call_command.assert_called_once_with("prune_scrapes")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_publish_ml_product(mock_call_command):
    """Verify that the run_publish_ml_product task calls the correct management command."""
    run_publish_ml_product()
    mock_call_command.assert_called_once_with("publish_ml_product")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_scrape_tecnomega(mock_call_command):
    """Verify that the run_scrape_tecnomega task calls the correct management command."""
    run_scrape_tecnomega()
    mock_call_command.assert_called_once_with("scrape_tecnomega")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_sync_price_list(mock_call_command):
    """Verify that the run_sync_price_list task calls the correct management command."""
    run_sync_price_list()
    mock_call_command.assert_called_once_with("sync_price_list")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_update_ml_eligibility(mock_call_command):
    """Verify that the run_update_ml_eligibility task calls the correct management command."""
    run_update_ml_eligibility()
    mock_call_command.assert_called_once_with("update_ml_eligibility")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_sync_ml_listings(mock_call_command):
    """Verify that the run_sync_ml_listings task calls the correct management command."""
    run_sync_ml_listings()
    mock_call_command.assert_called_once_with("sync_ml_listings")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_enrich_products_gtin(mock_call_command):
    """Verify that the run_enrich_products_gtin task calls the correct management command."""
    run_enrich_products_gtin()
    mock_call_command.assert_called_once_with("enrich_products_gtin")
