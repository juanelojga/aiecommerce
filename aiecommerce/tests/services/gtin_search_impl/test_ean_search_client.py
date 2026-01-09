import unittest
from unittest.mock import patch

import requests

from aiecommerce.services.gtin_search_impl.ean_search_client import EANSearchClient


class TestEANSearchClient(unittest.TestCase):
    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.settings")
    def test_init(self, mock_settings, mock_ean_search):
        mock_settings.EAN_SEARCH_TOKEN = "test-token"
        client = EANSearchClient()
        mock_ean_search.assert_called_once_with(token="test-token")
        self.assertIsNotNone(client.client)

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_yields_products(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        mock_ean_instance.productSearch.side_effect = [[{"ean": "123", "name": "Product 1"}, {"ean": "456", "name": "Product 2"}], None]

        client = EANSearchClient()
        results = list(client.search("query"))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["ean"], "123")
        self.assertEqual(results[1]["ean"], "456")

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_products_lazy_pagination(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        # Mock 3 pages of results
        mock_ean_instance.productSearch.side_effect = [
            [{"ean": "1"}],
            [{"ean": "2"}],
            [],  # Empty list stops the loop
        ]

        client = EANSearchClient()
        pages = list(client.search_products_lazy("query"))

        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["productlist"], [{"ean": "1"}])
        self.assertEqual(pages[1]["productlist"], [{"ean": "2"}])

        self.assertEqual(mock_ean_instance.productSearch.call_count, 3)
        mock_ean_instance.productSearch.assert_any_call("query", page=0)
        mock_ean_instance.productSearch.assert_any_call("query", page=1)
        mock_ean_instance.productSearch.assert_any_call("query", page=2)

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_products_lazy_stops_at_limit(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        # Always return a product to test the limit
        mock_ean_instance.productSearch.return_value = [{"ean": "limit-test"}]

        client = EANSearchClient()
        # It should stop after page 11 (since page starts at 0 and limit is page > 10)
        pages = list(client.search_products_lazy("query"))

        self.assertEqual(len(pages), 12)  # pages 0 to 11
        self.assertEqual(mock_ean_instance.productSearch.call_count, 12)

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_products_lazy_timeout(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        mock_ean_instance.productSearch.side_effect = requests.exceptions.Timeout()

        client = EANSearchClient()
        pages = list(client.search_products_lazy("query"))

        self.assertEqual(len(pages), 0)
        mock_ean_instance.productSearch.assert_called_once()

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_products_lazy_generic_exception(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        mock_ean_instance.productSearch.side_effect = Exception("API Error")

        client = EANSearchClient()
        pages = list(client.search_products_lazy("query"))

        self.assertEqual(len(pages), 0)
        mock_ean_instance.productSearch.assert_called_once()

    @patch("aiecommerce.services.gtin_search_impl.ean_search_client.EANSearch")
    def test_search_products_lazy_invalid_response(self, mock_ean_search_class):
        mock_ean_instance = mock_ean_search_class.return_value
        # Test various non-list returns
        mock_ean_instance.productSearch.side_effect = [None, {"not": "a list"}, "string", []]

        client = EANSearchClient()

        # None
        pages = list(client.search_products_lazy("query"))
        self.assertEqual(len(pages), 0)

        # Dict
        mock_ean_instance.productSearch.side_effect = [{"not": "a list"}]
        pages = list(client.search_products_lazy("query"))
        self.assertEqual(len(pages), 0)

        # String
        mock_ean_instance.productSearch.side_effect = ["string"]
        pages = list(client.search_products_lazy("query"))
        self.assertEqual(len(pages), 0)
