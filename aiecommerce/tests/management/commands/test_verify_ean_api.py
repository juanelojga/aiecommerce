import io
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from aiecommerce.models import ProductMaster


@pytest.mark.django_db
class TestVerifyEanApiCommand:
    @patch("aiecommerce.management.commands.verify_ean_api.ProductMaster.objects.get")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchClient")
    @patch("aiecommerce.management.commands.verify_ean_api.ProductMatcher")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchAPIStrategy")
    def test_verify_ean_api_success(
        self,
        mock_strategy_class,
        mock_matcher_class,
        mock_client_class,
        mock_get_product,
    ):
        # Setup mock product
        mock_product = MagicMock(spec=ProductMaster)
        mock_product.description = "Test Product"
        mock_product.sku = "SKU123"
        mock_get_product.return_value = mock_product

        # Setup mock strategy
        mock_strategy = mock_strategy_class.return_value
        mock_strategy.search_for_gtin.return_value = "1234567890123"

        out = io.StringIO()
        call_command("verify_ean_api", "SKU123", stdout=out)

        output = out.getvalue()
        assert "Current Cache Backend:" in output
        assert "Verifying EAN API for product: Test Product (SKU: SKU123)" in output
        assert "Found GTIN: 1234567890123" in output

        # Verify strategy was called
        mock_strategy.search_for_gtin.assert_called_once_with(mock_product)

    @patch("aiecommerce.management.commands.verify_ean_api.ProductMaster.objects.get")
    def test_verify_ean_api_product_not_found(self, mock_get_product):
        mock_get_product.side_effect = ProductMaster.DoesNotExist

        out = io.StringIO()
        call_command("verify_ean_api", "NONEXISTENT", stdout=out)

        output = out.getvalue()
        assert "Product with SKU 'NONEXISTENT' not found." in output

    @patch("aiecommerce.management.commands.verify_ean_api.ProductMaster.objects.get")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchClient")
    @patch("aiecommerce.management.commands.verify_ean_api.ProductMatcher")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchAPIStrategy")
    def test_verify_ean_api_no_gtin_found(
        self,
        mock_strategy_class,
        mock_matcher_class,
        mock_client_class,
        mock_get_product,
    ):
        mock_product = MagicMock(spec=ProductMaster)
        mock_product.description = "Test Product"
        mock_product.sku = "SKU123"
        mock_get_product.return_value = mock_product

        mock_strategy = mock_strategy_class.return_value
        mock_strategy.search_for_gtin.return_value = None

        out = io.StringIO()
        call_command("verify_ean_api", "SKU123", stdout=out)

        output = out.getvalue()
        assert "No GTIN found." in output

    @patch("aiecommerce.management.commands.verify_ean_api.cache")
    @patch("aiecommerce.management.commands.verify_ean_api.ProductMaster.objects.get")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchClient")
    @patch("aiecommerce.management.commands.verify_ean_api.ProductMatcher")
    @patch("aiecommerce.management.commands.verify_ean_api.EANSearchAPIStrategy")
    def test_verify_ean_api_clear_cache(
        self,
        mock_strategy_class,
        mock_matcher_class,
        mock_client_class,
        mock_get_product,
        mock_cache,
    ):
        mock_product = MagicMock(spec=ProductMaster)
        mock_product.description = "Test Product"
        mock_product.sku = "SKU123"
        mock_get_product.return_value = mock_product

        mock_strategy = mock_strategy_class.return_value
        mock_strategy._get_query.side_effect = ["query_model", "query_sku"]
        mock_strategy._get_cache_key.side_effect = ["key_model", "key_sku"]
        mock_strategy.search_for_gtin.return_value = "1234567890123"

        out = io.StringIO()
        call_command("verify_ean_api", "SKU123", "--clear-cache", stdout=out)

        output = out.getvalue()
        assert "Clearing cache..." in output
        assert "Cleared cache for query: 'query_model'" in output
        assert "Cleared cache for query: 'query_sku'" in output

        assert mock_cache.delete.call_count == 2
        mock_cache.delete.assert_any_call("key_model")
        mock_cache.delete.assert_any_call("key_sku")
