import unittest
from unittest.mock import MagicMock, patch

from aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator import TecnomegaDetailOrchestrator


class TestTecnomegaDetailOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mock_selector = MagicMock()
        self.mock_fetcher = MagicMock()
        self.mock_parser = MagicMock()
        self.orchestrator = TecnomegaDetailOrchestrator(selector=self.mock_selector, fetcher=self.mock_fetcher, parser=self.mock_parser)

    def test_run_no_products(self):
        # Setup: Queryset count is 0
        self.mock_selector.get_queryset.return_value.count.return_value = 0

        stats = self.orchestrator.run(force=False, dry_run=False)

        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["processed"], 0)
        self.mock_selector.get_queryset.assert_called_once_with(False, False)

    def test_run_dry_run(self):
        # Setup: Queryset returns one product
        mock_product = MagicMock()
        mock_product.code = "P123"
        self.mock_selector.get_queryset.return_value.count.return_value = 1
        self.mock_selector.get_queryset.return_value.iterator.return_value = [mock_product]

        stats = self.orchestrator.run(force=False, dry_run=True)

        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["processed"], 0)
        self.mock_fetcher.fetch_product_detail_html.assert_not_called()

    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.ProductDetailScrape")
    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.transaction.atomic")
    def test_run_success(self, mock_atomic, mock_scrape_model):
        # Setup: Queryset returns one product with code
        mock_product = MagicMock()
        mock_product.code = "P123"
        mock_product.sku = None
        self.mock_selector.get_queryset.return_value.count.return_value = 1
        self.mock_selector.get_queryset.return_value.iterator.return_value = [mock_product]

        self.mock_fetcher.fetch_product_detail_html.return_value = "<html></html>"
        self.mock_parser.parse.return_value = {"name": "Product Name", "price": 100.0, "currency": "USD", "attributes": {"sku": "SKU123"}, "images": ["img1.jpg"]}

        stats = self.orchestrator.run(force=False, dry_run=False, delay=0)

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(mock_product.sku, "SKU123")
        mock_product.save.assert_called_once_with(update_fields=["sku"])

        mock_scrape_model.objects.update_or_create.assert_called_once()
        args, kwargs = mock_scrape_model.objects.update_or_create.call_args
        self.assertEqual(kwargs["product"], mock_product)
        self.assertEqual(kwargs["name"], "Product Name")
        self.assertEqual(kwargs["attributes"], {"sku": "SKU123"})

    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.transaction.atomic")
    def test_run_no_sku_found(self, mock_atomic):
        # Setup: Queryset returns one product, but parser finds no SKU
        mock_product = MagicMock()
        mock_product.code = "P123"
        self.mock_selector.get_queryset.return_value.count.return_value = 1
        self.mock_selector.get_queryset.return_value.iterator.return_value = [mock_product]

        self.mock_fetcher.fetch_product_detail_html.return_value = "<html></html>"
        self.mock_parser.parse.return_value = {
            "attributes": {}  # No SKU here
        }

        stats = self.orchestrator.run(force=False, dry_run=False, delay=0)

        # Should still increment processed count because it was "handled"
        self.assertEqual(stats["processed"], 1)
        mock_product.save.assert_not_called()

    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.time.sleep")
    def test_run_exception_during_processing(self, mock_sleep):
        # Setup: Fetcher raises an exception
        mock_product = MagicMock()
        mock_product.code = "P123"
        self.mock_selector.get_queryset.return_value.count.return_value = 1
        self.mock_selector.get_queryset.return_value.iterator.return_value = [mock_product]

        self.mock_fetcher.fetch_product_detail_html.side_effect = Exception("Fetch failed")

        stats = self.orchestrator.run(force=False, dry_run=False, delay=1.0)

        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["total"], 1)
        mock_sleep.assert_called_once_with(1.0)

    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.time.sleep")
    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.ProductDetailScrape")
    @patch("aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator.transaction.atomic")
    def test_run_multiple_products(self, mock_atomic, mock_scrape_model, mock_sleep):
        # Setup: Queryset returns two products
        p1 = MagicMock()
        p1.code = "P1"
        p1.sku = None

        p2 = MagicMock()
        p2.code = "P2"
        p2.sku = None

        self.mock_selector.get_queryset.return_value.count.return_value = 2
        self.mock_selector.get_queryset.return_value.iterator.return_value = [p1, p2]

        self.mock_fetcher.fetch_product_detail_html.return_value = "<html></html>"
        self.mock_parser.parse.return_value = {
            "name": "Product",
            "attributes": {"sku": "SKU"},
        }

        stats = self.orchestrator.run(force=False, dry_run=False, delay=0.5)

        self.assertEqual(stats["processed"], 2)
        self.assertEqual(self.mock_fetcher.fetch_product_detail_html.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(0.5)
