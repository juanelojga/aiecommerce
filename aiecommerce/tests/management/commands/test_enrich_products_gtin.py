"""Tests for the enrich_products_gtin management command."""

import io
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.management.commands.enrich_products_gtin import Command as GTINCommand
from aiecommerce.models import ProductMaster


def _make_command() -> Any:
    """Create a command instance with captured stdout/stderr."""
    cmd = cast(Any, GTINCommand())
    cmd.stdout = io.StringIO()
    cmd.stderr = io.StringIO()
    return cmd


@pytest.mark.django_db
class TestEnrichProductsGTINCommand:
    """Test suite for enrich_products_gtin management command."""

    def test_handle_with_no_products(self, monkeypatch):
        """Test command when no products need GTIN enrichment."""
        # Mock the GTINSearchService to avoid configuration errors
        mock_service = MagicMock()

        cmd = _make_command()

        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            # Run command
            cmd.handle(limit=1)

        output = cmd.stdout.getvalue()

        # Should indicate no products found
        assert "No products found that need GTIN enrichment" in output
        # Service should be initialized but search should not be called
        assert mock_service.search_gtin.call_count == 0

    def test_handle_with_successful_gtin_found(self, monkeypatch):
        """Test command successfully finds GTIN for products."""
        # Create test products
        product1 = ProductMaster.objects.create(
            code="TEST001",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
            sku="SKU001",
            normalized_name="Test Product 001",
        )

        product2 = ProductMaster.objects.create(
            code="TEST002",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
            sku="SKU002",
            normalized_name="Test Product 002",
        )

        # Mock the GTINSearchService
        mock_service = MagicMock()
        # First call returns GTIN, second call returns NOT_FOUND
        mock_service.search_gtin.side_effect = [
            ("1234567890123", "sku_normalized_name"),
            (None, "NOT_FOUND"),
        ]

        cmd = _make_command()

        # Patch GTINSearchService in the command module
        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=2)

        output = cmd.stdout.getvalue()

        # Verify output messages
        assert "Starting GTIN enrichment" in output
        assert "Found 2 product(s) to process" in output
        assert "Processing product: TEST001" in output
        assert "Processing product: TEST002" in output
        assert "GTIN found: 1234567890123" in output
        assert "GTIN not found" in output
        assert "GTIN Enrichment Complete" in output
        assert "Total processed:  2" in output
        assert "GTIN found:       1" in output
        assert "GTIN not found:   1" in output

        # Verify database updates
        product1.refresh_from_db()
        assert product1.gtin == "1234567890123"
        assert product1.gtin_source == "sku_normalized_name"

        product2.refresh_from_db()
        assert product2.gtin is None
        assert product2.gtin_source == "NOT_FOUND"

    def test_handle_with_custom_limit(self, monkeypatch):
        """Test command respects custom limit parameter."""
        # Create 5 test products
        for i in range(5):
            ProductMaster.objects.create(
                code=f"TEST{i:03d}",
                is_active=True,
                is_for_mercadolibre=True,
                gtin=None,
                gtin_source=None,
                sku=f"SKU{i:03d}",
                normalized_name=f"Test Product {i:03d}",
            )

        mock_service = MagicMock()
        mock_service.search_gtin.return_value = ("1234567890123", "sku_normalized_name")

        cmd = _make_command()

        # Run with limit of 3
        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=3)

        output = cmd.stdout.getvalue()

        # Should only process 3 products
        assert "Found 3 product(s) to process" in output
        assert "[1/3]" in output
        assert "[2/3]" in output
        assert "[3/3]" in output
        assert "[4/" not in output  # Should not process more than limit

    def test_handle_with_error_handling(self, monkeypatch):
        """Test command handles errors gracefully."""
        # Create test product
        ProductMaster.objects.create(
            code="ERROR_TEST",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
            sku="SKU_ERROR",
            normalized_name="Error Test Product",
        )

        # Mock service to raise an exception
        mock_service = MagicMock()
        mock_service.search_gtin.side_effect = Exception("API Error")

        cmd = _make_command()

        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=1)

        output = cmd.stdout.getvalue()

        # Should show error message
        assert "Error processing product ERROR_TEST" in output
        assert "API Error" in output
        assert "Errors:           1" in output

    def test_handle_selector_excludes_not_found_products(self):
        """Test that selector properly excludes products with NOT_FOUND source."""
        # Create product already marked as NOT_FOUND
        ProductMaster.objects.create(
            code="ALREADY_SEARCHED",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source="NOT_FOUND",
            sku="SKU_SEARCHED",
            normalized_name="Already Searched Product",
        )

        # Create product that should be processed
        ProductMaster.objects.create(
            code="NEW_PRODUCT",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
            sku="SKU_NEW",
            normalized_name="New Product",
        )

        mock_service = MagicMock()
        mock_service.search_gtin.return_value = ("9999999999999", "model_brand")

        cmd = _make_command()

        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=1)

        output = cmd.stdout.getvalue()

        # Should only process 1 product (NEW_PRODUCT)
        assert "Found 1 product(s) to process" in output
        assert "Processing product: NEW_PRODUCT" in output
        assert "ALREADY_SEARCHED" not in output

    def test_handle_progress_logging(self, monkeypatch):
        """Test that command logs progress for each product."""
        # Create 3 test products
        for i in range(3):
            ProductMaster.objects.create(
                code=f"PROD{i}",
                is_active=True,
                is_for_mercadolibre=True,
                gtin=None,
                gtin_source=None,
                sku=f"SKU_PROD{i}",
                normalized_name=f"Product {i}",
            )

        mock_service = MagicMock()
        # Return different results for each product
        mock_service.search_gtin.side_effect = [
            ("1111111111111", "sku_normalized_name"),
            ("2222222222222", "model_brand"),
            (None, "NOT_FOUND"),
        ]

        cmd = _make_command()

        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=3)

        output = cmd.stdout.getvalue()

        # Verify progress messages for each product
        assert "[1/3] Processing product: PROD0" in output
        assert "[2/3] Processing product: PROD1" in output
        assert "[3/3] Processing product: PROD2" in output

        # Verify individual results
        assert "GTIN found: 1111111111111" in output
        assert "strategy: sku_normalized_name" in output
        assert "GTIN found: 2222222222222" in output
        assert "strategy: model_brand" in output
        assert "GTIN not found" in output

    def test_handle_excludes_products_with_existing_gtin(self):
        """Test that products with existing GTIN are not processed."""
        # Create product with existing GTIN
        ProductMaster.objects.create(
            code="HAS_GTIN",
            is_active=True,
            is_for_mercadolibre=True,
            gtin="1234567890123",
            gtin_source="sku_normalized_name",
            sku="SKU_HAS",
            normalized_name="Has GTIN Product",
        )

        # Create product without GTIN
        ProductMaster.objects.create(
            code="NO_GTIN",
            is_active=True,
            is_for_mercadolibre=True,
            gtin=None,
            gtin_source=None,
            sku="SKU_NO",
            normalized_name="No GTIN Product",
        )

        mock_service = MagicMock()
        mock_service.search_gtin.return_value = ("9999999999999", "model_brand")

        cmd = _make_command()

        with patch(
            "aiecommerce.management.commands.enrich_products_gtin.GTINSearchService",
            return_value=mock_service,
        ):
            cmd.handle(limit=1)

        output = cmd.stdout.getvalue()

        # Should only process product without GTIN
        assert "Found 1 product(s) to process" in output
        assert "Processing product: NO_GTIN" in output
        assert "HAS_GTIN" not in output
