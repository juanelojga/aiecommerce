from unittest.mock import Mock, patch

import pytest

from aiecommerce.services.mercadolibre_impl.category_predictor import CategoryPredictorService
from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError


@pytest.fixture
def mock_ml_client() -> Mock:
    """Fixture for a mocked MercadoLibreClient."""
    return Mock(spec=MercadoLibreClient)


@pytest.fixture
def category_predictor_service(mock_ml_client: Mock) -> CategoryPredictorService:
    """Fixture for CategoryPredictorService with a mocked client and site_id."""
    return CategoryPredictorService(client=mock_ml_client, site_id="MLM")


def test_predict_category_success(category_predictor_service: CategoryPredictorService, mock_ml_client: Mock):
    """
    Tests that predict_category returns the category_id on a successful API call
    with the correct endpoint and query parameter.
    """
    # Arrange
    expected_category_id = "MLA1055"
    api_response = [{"domain_id": "MLA-CELLPHONES", "domain_name": "Celulares", "category_id": expected_category_id, "category_name": "Celulares y Smartphones", "attributes": []}]
    mock_ml_client.get.return_value = api_response
    title = "A valid product title"

    # Act
    category_id = category_predictor_service.predict_category(title)

    # Assert
    assert category_id == expected_category_id
    mock_ml_client.get.assert_called_once_with("/sites/MLM/domain_discovery/search", params={"q": title, "limit": 1})


def test_predict_category_empty_response(category_predictor_service: CategoryPredictorService, mock_ml_client: Mock):
    """
    Tests that predict_category returns None when the API returns an empty list.
    """
    # Arrange
    mock_ml_client.get.return_value = []
    title = "A product title with no category"

    # Act
    category_id = category_predictor_service.predict_category(title)

    # Assert
    assert category_id is None
    mock_ml_client.get.assert_called_once_with("/sites/MLM/domain_discovery/search", params={"q": title, "limit": 1})


def test_predict_category_api_error(category_predictor_service: CategoryPredictorService, mock_ml_client: Mock):
    """
    Tests that predict_category returns None when the client raises an API error.
    """
    # Arrange
    mock_ml_client.get.side_effect = MLAPIError("API is down")
    title = "A product title"

    # Act
    with patch("aiecommerce.services.mercadolibre_impl.category_predictor.logger") as mock_logger:
        category_id = category_predictor_service.predict_category(title)

    # Assert
    assert category_id is None
    mock_logger.error.assert_called_once()
    mock_ml_client.get.assert_called_once_with("/sites/MLM/domain_discovery/search", params={"q": title, "limit": 1})


def test_predict_category_malformed_response(category_predictor_service: CategoryPredictorService, mock_ml_client: Mock):
    """
    Tests that predict_category returns None for a malformed API response (e.g., missing category_id).
    """
    # Arrange
    api_response = [
        {
            "domain_id": "MLA-CELLPHONES",
            "domain_name": "Celulares",
            # "category_id": expected_category_id, # Missing category_id
            "category_name": "Celulares y Smartphones",
            "attributes": [],
        }
    ]
    mock_ml_client.get.return_value = api_response
    title = "A product title"

    # Act
    with patch("aiecommerce.services.mercadolibre_impl.category_predictor.logger") as mock_logger:
        category_id = category_predictor_service.predict_category(title)

    # Assert
    assert category_id is None
    mock_logger.warning.assert_called_once()
    mock_ml_client.get.assert_called_once_with("/sites/MLM/domain_discovery/search", params={"q": title, "limit": 1})


def test_predict_category_empty_title(mock_ml_client: Mock):
    """
    Tests that predict_category returns None and does not call the client if the title is empty.
    """
    # Arrange
    service = CategoryPredictorService(client=mock_ml_client, site_id="MLM")

    # Act
    with patch("aiecommerce.services.mercadolibre_impl.category_predictor.logger") as mock_logger:
        category_id = service.predict_category("")

    # Assert
    assert category_id is None
    mock_ml_client.get.assert_not_called()
    mock_logger.warning.assert_called_once_with("Title is empty, cannot predict category.")
