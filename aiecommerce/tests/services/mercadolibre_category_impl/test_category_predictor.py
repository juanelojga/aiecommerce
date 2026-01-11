from unittest.mock import MagicMock

import pytest

from aiecommerce.services.mercadolibre_category_impl.category_predictor import MercadolibreCategoryPredictorService
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError


class TestMercadolibreCategoryPredictorService:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def site_id(self):
        return "MLC"

    @pytest.fixture
    def service(self, mock_client, site_id):
        return MercadolibreCategoryPredictorService(client=mock_client, site_id=site_id)

    def test_predict_category_success(self, service, mock_client, site_id):
        # Setup
        title = "Smartphone Samsung Galaxy S21"
        category_id = "MLC1051"
        mock_client.get.return_value = [{"category_id": category_id}]

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result == category_id
        mock_client.get.assert_called_once_with(f"/sites/{site_id}/domain_discovery/search", params={"q": title, "limit": 1})

    def test_predict_category_empty_title(self, service, mock_client):
        # Execute
        result = service.predict_category("")

        # Assertions
        assert result is None
        mock_client.get.assert_not_called()

    def test_predict_category_none_title(self, service, mock_client):
        # Execute
        result = service.predict_category(None)

        # Assertions
        assert result is None
        mock_client.get.assert_not_called()

    def test_predict_category_empty_response(self, service, mock_client, site_id):
        # Setup
        title = "Some product"
        mock_client.get.return_value = []

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result is None
        mock_client.get.assert_called_once()

    def test_predict_category_malformed_response(self, service, mock_client, site_id):
        # Setup
        title = "Some product"
        mock_client.get.return_value = [{"not_category_id": "something"}]

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result is None
        mock_client.get.assert_called_once()

    def test_predict_category_ml_api_error(self, service, mock_client):
        # Setup
        title = "Some product"
        mock_client.get.side_effect = MLAPIError("API Error")

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result is None
        mock_client.get.assert_called_once()

    def test_predict_category_index_error(self, service, mock_client):
        # Setup
        title = "Some product"
        # This will trigger IndexError when accessing response[0] if it's an empty list,
        # but the code handles `if response and isinstance(response, list) and response[0].get("category_id")`
        # Wait, if response is empty list [], `response[0]` WILL raise IndexError.
        # But `if response` for `[]` is False in Python. So it shouldn't reach response[0].

        # Let's force an IndexError somehow if possible, or just rely on the fact that
        # the catch block is there.
        # Actually, if response is `True` but empty? No.
        # If response = [{}], then response[0].get("category_id") is None.

        # What if mock_client.get returns something that is truthy and a list but accessing [0] fails?
        # Hard to do with a real list.

        # Let's mock the response to be something that raises IndexError on access.
        mock_response = MagicMock()
        mock_response.__len__.return_value = 1
        mock_response.__getitem__.side_effect = IndexError("Index error")
        mock_client.get.return_value = mock_response

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result is None
        mock_client.get.assert_called_once()

    def test_predict_category_key_error(self, service, mock_client):
        # Setup
        title = "Some product"

        # Force KeyError during response[0].get("category_id")
        # Wait, .get() doesn't raise KeyError.
        # But the code says `return response[0]["category_id"]` on line 36!
        # Ah!
        # 35:            if response and isinstance(response, list) and response[0].get("category_id"):
        # 36:                return response[0]["category_id"]

        # If .get("category_id") is truthy, then ["category_id"] will not raise KeyError.

        # How could it raise KeyError?
        # Maybe if response[0] is not a dict? But .get() would fail with AttributeError then.

        # Let's look at the code again:
        # 42:        except (IndexError, KeyError) as e:

        # Maybe it was written defensively.

        mock_client.get.side_effect = KeyError("Key error")

        # Execute
        result = service.predict_category(title)

        # Assertions
        assert result is None
        mock_client.get.assert_called_once()
