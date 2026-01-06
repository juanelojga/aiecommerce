from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from model_bakery import baker

from aiecommerce.models import ProductDetailScrape, ProductMaster

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    """Fixture to create a ProductMaster instance."""
    return baker.make(ProductMaster, code="TEST001", description="A test product")


def test_handle_product_not_found():
    """Test that the command raises CommandError if the product code does not exist."""
    with pytest.raises(CommandError) as excinfo:
        call_command("sync_tecnomega_details", "NONEXISTENT")
    assert "ProductMaster with code 'NONEXISTENT' not found" in str(excinfo.value)


@patch("aiecommerce.management.commands.sync_tecnomega_details.TecnomegaDetailParser")
@patch("aiecommerce.management.commands.sync_tecnomega_details.TecnomegaDetailFetcher")
def test_handle_dry_run_mode(mock_fetcher, mock_parser, product):
    """Test that in --dry-run mode, the command fetches and parses but does not save."""
    # Arrange
    out = StringIO()
    mock_fetch_instance = mock_fetcher.return_value
    mock_fetch_instance.fetch_product_detail_html.return_value = "<html></html>"
    mock_parser_instance = mock_parser.return_value
    mock_parser_instance.parse.return_value = {"name": "Test Product", "price": 99.99}

    # Act
    call_command("sync_tecnomega_details", product.code, stdout=out)

    # Assert
    output = out.getvalue()
    assert "-- DRY RUN MODE --" in output
    assert '"name": "Test Product"' in output
    mock_fetch_instance.fetch_product_detail_html.assert_called_once_with(product.code)
    mock_parser_instance.parse.assert_called_once_with("<html></html>")
    # Verify no data was persisted
    assert ProductDetailScrape.objects.count() == 0


@patch("aiecommerce.management.commands.sync_tecnomega_details.TecnomegaDetailOrchestrator")
def test_handle_sync_success(mock_orchestrator, product):
    """Test the command successfully calls the orchestrator in live mode."""
    # Arrange
    out = StringIO()
    mock_orchestrator_instance = mock_orchestrator.return_value
    mock_orchestrator_instance.sync_details.return_value = True

    # Act
    call_command("sync_tecnomega_details", product.code, "--no-dry-run", stdout=out)

    # Assert
    output = out.getvalue()
    assert f"Successfully synced details for product: {product.code}" in output
    mock_orchestrator_instance.sync_details.assert_called_once_with(product, session_id="manual_sync")


@patch("aiecommerce.management.commands.sync_tecnomega_details.TecnomegaDetailOrchestrator")
def test_handle_sync_failure(mock_orchestrator, product):
    """Test the command reports a failure if the orchestrator returns False."""
    # Arrange
    out = StringIO()
    mock_orchestrator_instance = mock_orchestrator.return_value
    mock_orchestrator_instance.sync_details.return_value = False

    # Act
    call_command("sync_tecnomega_details", product.code, "--no-dry-run", stdout=out)

    # Assert
    output = out.getvalue()
    assert f"Failed to sync details for product: {product.code}" in output
    mock_orchestrator_instance.sync_details.assert_called_once_with(product, session_id="manual_sync")


@patch("aiecommerce.management.commands.sync_tecnomega_details.TecnomegaDetailFetcher.fetch_product_detail_html", side_effect=Exception("Fetch error"))
def test_dry_run_handles_fetch_exception(mock_fetch, product):
    """Test that a fetch exception during a dry run is caught and reported."""
    with pytest.raises(CommandError) as excinfo:
        call_command("sync_tecnomega_details", product.code)
    assert "Dry run failed: Fetch error" in str(excinfo.value)
