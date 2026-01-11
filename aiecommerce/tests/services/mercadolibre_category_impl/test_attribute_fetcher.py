from unittest.mock import MagicMock

import pytest

from aiecommerce.services.mercadolibre_category_impl.attribute_fetcher import MercadolibreCategoryAttributeFetcher


class TestMercadolibreCategoryAttributeFetcher:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def fetcher(self, mock_client):
        return MercadolibreCategoryAttributeFetcher(client=mock_client)

    def test_get_category_attributes_success(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_attributes = [
            {"id": "COLOR", "tags": ["required", "fixed"]},
            {"id": "SIZE", "tags": ["new_required"]},
            {"id": "MATERIAL", "tags": ["conditional_required"]},
            {"id": "BRAND", "tags": ["others"]},
            {"id": "MODEL", "tags": []},
            {"id": "WARRANTY", "tags": None},
            {"id": "EAN"},
        ]
        mock_client.get.return_value = mock_attributes

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert len(result) == 3
        assert result[0]["id"] == "COLOR"
        assert result[1]["id"] == "SIZE"
        assert result[2]["id"] == "MATERIAL"
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")

    def test_get_category_attributes_no_required(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_attributes = [
            {"id": "BRAND", "tags": ["others"]},
            {"id": "MODEL", "tags": []},
        ]
        mock_client.get.return_value = mock_attributes

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert result == []
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")

    def test_get_category_attributes_not_a_list(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_client.get.return_value = {"error": "not a list"}

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert result == []
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")

    def test_get_category_attributes_empty_response(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_client.get.return_value = []

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert result == []
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")

    def test_get_category_attributes_api_error(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_client.get.side_effect = Exception("API error")

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert result == []
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")

    def test_get_category_attributes_invalid_tags(self, fetcher, mock_client):
        # Setup
        category_id = "MLC1234"
        mock_attributes = [
            {"id": "ATTR1", "tags": "not a list"},
            {"id": "ATTR2", "tags": 123},
        ]
        mock_client.get.return_value = mock_attributes

        # Execute
        result = fetcher.get_category_attributes(category_id)

        # Assertions
        assert result == []
        mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")
