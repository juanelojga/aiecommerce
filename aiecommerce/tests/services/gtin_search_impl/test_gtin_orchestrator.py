import unittest
from unittest.mock import MagicMock

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_search_impl.orchestrator import GTINDiscoveryOrchestrator


class TestGTINDiscoveryOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mock_selector = MagicMock()
        self.mock_google_strategy = MagicMock()
        self.orchestrator = GTINDiscoveryOrchestrator(selector=self.mock_selector, google_strategy=self.mock_google_strategy)
        self.mock_product = MagicMock(spec=ProductMaster)
        self.mock_product.code = "TEST-SKU"
        self.mock_product.gtin = None
        self.mock_product.gtin_source = None

    def test_run_success(self):
        # Setup mock queryset
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.mock_product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        # Setup mock strategy return value
        self.mock_google_strategy.execute.return_value = {"gtin": "1234567890123", "gtin_source": "GOOGLE"}

        # Run the orchestrator
        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        # Assertions
        self.assertEqual(result, {"total": 1, "processed": 1})
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)
        self.assertEqual(self.mock_product.gtin, "1234567890123")
        self.assertEqual(self.mock_product.gtin_source, "GOOGLE")
        self.mock_product.save.assert_called_once_with(update_fields=["gtin", "gtin_source"])

    def test_run_no_products(self):
        # Setup mock queryset with 0 products
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 0
        self.mock_selector.get_queryset.return_value = mock_queryset

        # Run the orchestrator
        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        # Assertions
        self.assertEqual(result, {"total": 0, "processed": 0})
        self.mock_google_strategy.execute.assert_not_called()

    def test_run_dry_run_does_not_save(self):
        # Setup mock queryset
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.iterator.return_value = [self.mock_product]
        self.mock_selector.get_queryset.return_value = mock_queryset

        # Setup mock strategy return value
        self.mock_google_strategy.execute.return_value = {"gtin": "1234567890123", "gtin_source": "GOOGLE"}

        # Run the orchestrator with dry_run=True
        result = self.orchestrator.run(force=False, dry_run=True, delay=0)

        # Assertions
        self.assertEqual(result, {"total": 1, "processed": 1})
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)
        # Should NOT save when dry_run is True
        self.mock_product.save.assert_not_called()

    def test_run_exception_continues_processing(self):
        # Setup mock products
        product1 = MagicMock(spec=ProductMaster)
        product1.code = "SKU1"
        product2 = MagicMock(spec=ProductMaster)
        product2.code = "SKU2"

        # Setup mock queryset
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 2
        mock_queryset.iterator.return_value = [product1, product2]
        self.mock_selector.get_queryset.return_value = mock_queryset

        # First product fails, second succeeds
        self.mock_google_strategy.execute.side_effect = [Exception("Error"), {"gtin": "123", "gtin_source": "GOOGLE"}]

        # Run the orchestrator
        result = self.orchestrator.run(force=False, dry_run=False, delay=0)

        # Assertions
        self.assertEqual(result, {"total": 2, "processed": 2})
        self.assertEqual(self.mock_google_strategy.execute.call_count, 2)
        product2.save.assert_called_once()
