import unittest
from unittest.mock import MagicMock

from aiecommerce.models import ProductMaster
from aiecommerce.services.gtin_search_impl.orchestrator import GTINDiscoveryOrchestrator


class TestGTINDiscoveryOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mock_ean_strategy = MagicMock()
        self.mock_google_strategy = MagicMock()
        self.orchestrator = GTINDiscoveryOrchestrator(ean_api_strategy=self.mock_ean_strategy, google_strategy=self.mock_google_strategy)
        self.mock_product = MagicMock(spec=ProductMaster)
        self.mock_product.sku = "TEST-SKU"

    def test_discover_gtin_tier1_success(self):
        # Tier 1 returns a GTIN
        self.mock_ean_strategy.search_for_gtin.return_value = "1234567890123"

        result = self.orchestrator.discover_gtin(self.mock_product)

        self.assertEqual(result, {"gtin": "1234567890123", "source": "EAN_API"})
        self.mock_ean_strategy.search_for_gtin.assert_called_once_with(self.mock_product)
        self.mock_google_strategy.execute.assert_not_called()

    def test_discover_gtin_tier1_fail_tier2_success(self):
        # Tier 1 fails, Tier 2 succeeds
        self.mock_ean_strategy.search_for_gtin.return_value = None
        self.mock_google_strategy.execute.return_value = {"gtin": "0987654321098", "source": "GOOGLE"}

        result = self.orchestrator.discover_gtin(self.mock_product)

        self.assertEqual(result, {"gtin": "0987654321098", "source": "GOOGLE"})
        self.mock_ean_strategy.search_for_gtin.assert_called_once_with(self.mock_product)
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)

    def test_discover_gtin_all_tiers_fail(self):
        # Both tiers fail
        self.mock_ean_strategy.search_for_gtin.return_value = None
        self.mock_google_strategy.execute.return_value = None

        result = self.orchestrator.discover_gtin(self.mock_product)

        self.assertIsNone(result)
        self.mock_ean_strategy.search_for_gtin.assert_called_once_with(self.mock_product)
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)

    def test_discover_gtin_tier1_exception_falls_back_to_tier2(self):
        # Tier 1 raises exception, Tier 2 succeeds
        self.mock_ean_strategy.search_for_gtin.side_effect = Exception("Tier 1 Error")
        self.mock_google_strategy.execute.return_value = {"gtin": "5555555555555", "source": "GOOGLE"}

        result = self.orchestrator.discover_gtin(self.mock_product)

        self.assertEqual(result, {"gtin": "5555555555555", "source": "GOOGLE"})
        self.mock_ean_strategy.search_for_gtin.assert_called_once_with(self.mock_product)
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)

    def test_discover_gtin_tier2_exception_returns_none(self):
        # Tier 1 fails, Tier 2 raises exception
        self.mock_ean_strategy.search_for_gtin.return_value = None
        self.mock_google_strategy.execute.side_effect = Exception("Tier 2 Error")

        result = self.orchestrator.discover_gtin(self.mock_product)

        self.assertIsNone(result)
        self.mock_ean_strategy.search_for_gtin.assert_called_once_with(self.mock_product)
        self.mock_google_strategy.execute.assert_called_once_with(self.mock_product)
