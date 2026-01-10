import unittest
from unittest.mock import MagicMock

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.gtin_search_impl.google_search_strategy import GoogleGTINStrategy


class TestGoogleGTINStrategy(unittest.TestCase):
    def setUp(self):
        self.mock_google_client = MagicMock()
        self.search_engine_id = "test_cx"
        self.strategy = GoogleGTINStrategy(self.mock_google_client, self.search_engine_id)
        self.mock_product = MagicMock(spec=ProductMaster)
        self.mock_product.code = "TEST-PRODUCT"
        self.mock_product.specs = {}

    def test_extract_from_snippets_success(self):
        search_results = {
            "items": [
                {"snippet": "No GTIN here"},
                {"snippet": "Product with EAN 1234567890123 in snippet"},
            ]
        }
        result = self.strategy._extract_from_snippets(search_results)
        self.assertEqual(result, "1234567890123")

    def test_extract_from_snippets_no_gtin(self):
        search_results = {
            "items": [
                {"snippet": "No GTIN here"},
                {"snippet": "Short number 12345"},
            ]
        }
        result = self.strategy._extract_from_snippets(search_results)
        self.assertIsNone(result)

    def test_extract_from_snippets_empty_results(self):
        self.assertIsNone(self.strategy._extract_from_snippets({}))
        self.assertIsNone(self.strategy._extract_from_snippets({"items": []}))
        self.assertIsNone(self.strategy._extract_from_snippets(None))

    def test_extract_from_snippets_gtin_14_digits(self):
        search_results = {"items": [{"snippet": "GTIN-14: 12345678901234"}]}
        result = self.strategy._extract_from_snippets(search_results)
        self.assertEqual(result, "12345678901234")

    def test_execute_no_specs(self):
        self.mock_product.specs = None
        result = self.strategy.execute(self.mock_product)
        self.assertIsNone(result)
        self.mock_google_client.cse().list.assert_not_called()

    def test_execute_insufficient_specs(self):
        self.mock_product.specs = {"manufacturer": "Dell"}
        result = self.strategy.execute(self.mock_product)
        self.assertIsNone(result)
        self.mock_google_client.cse().list.assert_not_called()

    def test_execute_success(self):
        self.mock_product.specs = {"manufacturer": "Dell", "model_name": "XPS 13"}

        # Mocking the chain: self.google_client.cse().list(q=query, cx=self.search_engine_id).execute()
        mock_cse = self.mock_google_client.cse.return_value
        mock_list = mock_cse.list.return_value
        mock_list.execute.return_value = {"items": [{"snippet": "EAN: 9876543210987"}]}

        result = self.strategy.execute(self.mock_product)

        self.assertEqual(result, {"gtin": "9876543210987", "gtin_source": "google_search"})
        mock_cse.list.assert_called_once_with(q="Dell XPS 13 EAN GTIN barcode", cx=self.search_engine_id)

    def test_execute_no_results(self):
        self.mock_product.specs = {"manufacturer": "Dell", "model_name": "XPS 13"}

        mock_cse = self.mock_google_client.cse.return_value
        mock_list = mock_cse.list.return_value
        mock_list.execute.return_value = {"items": []}

        result = self.strategy.execute(self.mock_product)
        self.assertIsNone(result)

    def test_execute_with_all_specs(self):
        self.mock_product.specs = {"manufacturer": "Apple", "model_name": "MacBook Pro", "cpu": "M2", "chipset": "Apple Silicon", "ram": "16GB", "capacity": "512GB"}

        mock_cse = self.mock_google_client.cse.return_value
        mock_list = mock_cse.list.return_value
        mock_list.execute.return_value = {"items": [{"snippet": "Barcode 1112223334445"}]}

        result = self.strategy.execute(self.mock_product)

        self.assertEqual(result, {"gtin": "1112223334445", "gtin_source": "google_search"})
        expected_query = "Apple MacBook Pro M2 Apple Silicon 16GB 512GB EAN GTIN barcode"
        mock_cse.list.assert_called_once_with(q=expected_query, cx=self.search_engine_id)
