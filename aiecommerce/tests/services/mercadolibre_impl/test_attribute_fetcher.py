from unittest.mock import Mock, patch

import pytest

from aiecommerce.services.mercadolibre_impl.attribute_fetcher import (
    CategoryAttributeFetcher,
)
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient


@pytest.fixture
def mock_client():
    """Fixture for a mocked MercadoLibreClient."""
    return Mock(spec=MercadoLibreClient)


def test_get_required_attributes_happy_path(mock_client):
    """
    Verify that get_required_attributes correctly filters for mandatory attributes.
    """
    # Arrange
    category_id = "MLM1234"
    api_response = [
        {"id": "BRAND", "name": "Brand", "tags": {"required": True}},
        {"id": "MODEL", "name": "Model", "tags": {"new_required": True}},
        {"id": "COLOR", "name": "Color", "tags": {"hidden": True}},
        {"id": "GPU", "name": "GPU Model", "tags": {"conditional_required": True}},
        {"id": "WEIGHT", "name": "Weight", "tags": {"read_only": True}},
    ]
    mock_client.get.return_value = api_response
    fetcher = CategoryAttributeFetcher(client=mock_client)

    # Act
    required_attributes = fetcher.get_required_attributes(category_id)

    # Assert
    mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")
    assert len(required_attributes) == 3
    assert required_attributes[0]["id"] == "BRAND"
    assert required_attributes[1]["id"] == "MODEL"
    assert required_attributes[2]["id"] == "GPU"


def test_get_required_attributes_no_required_found(mock_client):
    """
    Verify behavior when the API returns attributes but none are required.
    """
    # Arrange
    category_id = "MLM5678"
    api_response = [
        {"id": "COLOR", "name": "Color", "tags": {"hidden": True}},
        {"id": "WEIGHT", "name": "Weight", "tags": {"read_only": True}},
    ]
    mock_client.get.return_value = api_response
    fetcher = CategoryAttributeFetcher(client=mock_client)

    # Act
    required_attributes = fetcher.get_required_attributes(category_id)

    # Assert
    mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")
    assert len(required_attributes) == 0


def test_get_required_attributes_api_exception(mock_client):
    """
    Verify that the method returns an empty list and logs an error on API failure.
    """
    # Arrange
    category_id = "MLM_ERROR"
    mock_client.get.side_effect = Exception("API connection failed")
    fetcher = CategoryAttributeFetcher(client=mock_client)

    # Act
    with patch("aiecommerce.services.mercadolibre_impl.attribute_fetcher.logger") as mock_logger:
        required_attributes = fetcher.get_required_attributes(category_id)

        # Assert
        assert required_attributes == []
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert f"Error fetching attributes for category_id {category_id}" in args[0]


def test_get_required_attributes_empty_response(mock_client):
    """
    Verify behavior with an empty list of attributes from the API.
    """
    # Arrange
    category_id = "MLM_EMPTY"
    mock_client.get.return_value = []
    fetcher = CategoryAttributeFetcher(client=mock_client)

    # Act
    required_attributes = fetcher.get_required_attributes(category_id)

    # Assert
    assert required_attributes == []
    mock_client.get.assert_called_once_with(f"categories/{category_id}/attributes")


def test_attribute_missing_tags_key(mock_client):
    """
    Verify that attributes without a 'tags' key are handled gracefully.
    """
    # Arrange
    category_id = "MLM_NO_TAGS"
    api_response = [
        {"id": "BRAND", "name": "Brand", "tags": {"required": True}},
        {"id": "MODEL", "name": "Model"},  # No 'tags' key
    ]
    mock_client.get.return_value = api_response
    fetcher = CategoryAttributeFetcher(client=mock_client)

    # Act
    required_attributes = fetcher.get_required_attributes(category_id)

    # Assert
    assert len(required_attributes) == 1
    assert required_attributes[0]["id"] == "BRAND"
