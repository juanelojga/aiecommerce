from unittest.mock import MagicMock, patch

import pytest
import requests

from aiecommerce.services.mercadolibre_impl.client import MercadoLibreClient, MercadoLibreConfig
from aiecommerce.services.mercadolibre_impl.exceptions import MLAPIError, MLRateLimitError, MLTokenExpiredError


@pytest.fixture
def mock_settings():
    with patch("aiecommerce.services.mercadolibre_impl.client.settings") as mock:
        mock.MERCADOLIBRE_CLIENT_ID = "test_client_id"
        mock.MERCADOLIBRE_CLIENT_SECRET = "test_client_secret"
        mock.MERCADOLIBRE_BASE_URL = "https://api.mercadolibre.com"
        yield mock


@pytest.fixture
def config():
    return MercadoLibreConfig(client_id="id", client_secret="secret", base_url="https://test.api.com", timeout=10, max_retries=2, backoff_factor=1.0)


@pytest.fixture
def client(config):
    return MercadoLibreClient(access_token="test_token", config=config)


class TestMercadoLibreConfig:
    def test_default_values(self):
        config = MercadoLibreConfig(client_id="id", client_secret="secret")
        assert config.base_url == "https://api.mercadolibre.com"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.backoff_factor == 2.0


class TestMercadoLibreClientInit:
    def test_init_with_config(self, config):
        client = MercadoLibreClient(access_token="token", config=config)
        assert client.access_token == "token"
        assert client.config == config

    def test_init_without_config(self, mock_settings):
        client = MercadoLibreClient(access_token="token")
        assert client.access_token == "token"
        assert client.config.client_id == "test_client_id"
        assert client.config.client_secret == "test_client_secret"
        assert client.config.base_url == "https://api.mercadolibre.com"


class TestMercadoLibreClientInternal:
    def test_get_headers_success(self, client):
        headers = client._get_headers()
        assert headers == {"Authorization": "Bearer test_token"}

    def test_get_headers_no_token(self, config):
        client = MercadoLibreClient(access_token=None, config=config)
        with pytest.raises(MLAPIError, match="No access token provided"):
            client._get_headers()

    def test_mask_sensitive_data(self, client):
        data = {
            "client_id": "secret_id",
            "client_secret": "secret_pass",
            "access_token": "secret_token",
            "refresh_token": "secret_refresh",
            "code": "secret_code",
            "public": "visible",
        }
        masked = client._mask_sensitive_data(data)
        assert masked["client_id"] == "***"
        assert masked["client_secret"] == "***"
        assert masked["access_token"] == "***"
        assert masked["refresh_token"] == "***"
        assert masked["code"] == "***"
        assert masked["public"] == "visible"

    def test_handle_response_success(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        response.json.return_value = {"key": "value"}
        response.content = b'{"key": "value"}'

        result = client._handle_response(response)
        assert result == {"key": "value"}

    def test_handle_response_empty_content(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 204
        response.content = b""

        result = client._handle_response(response)
        assert result == {}

    def test_handle_response_invalid_json(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        response.content = b"invalid json"
        response.json.side_effect = ValueError()
        response.text = "invalid json"

        result = client._handle_response(response)
        assert result == {"raw_body": "invalid json"}

    def test_handle_response_401(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 401

        with pytest.raises(MLTokenExpiredError, match="Token expired"):
            client._handle_response(response)

    def test_handle_response_429(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 429

        with pytest.raises(MLRateLimitError, match="Rate limit exceeded"):
            client._handle_response(response)

    def test_handle_response_http_error(self, client):
        response = MagicMock(spec=requests.Response)
        response.status_code = 500
        response.text = "Internal Server Error"
        response.raise_for_status.side_effect = requests.HTTPError(response=response)

        with pytest.raises(MLAPIError, match="HTTP Error 500"):
            client._handle_response(response)

    @patch("aiecommerce.services.mercadolibre_impl.client.requests.Session")
    def test_send_request_success(self, mock_session_class, client):
        mock_session = mock_session_class.return_value
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.content = b'{"status": "ok"}'
        mock_session.request.return_value = mock_response

        # We need to re-initialize client to use the mock session if it was created in __init__
        # Actually client._session is already created. Let's patch it directly.
        client._session = mock_session

        result = client._send_request("GET", "https://api.com/test")
        assert result == {"status": "ok"}
        mock_session.request.assert_called_once_with("GET", "https://api.com/test", timeout=client.config.timeout, headers={"Authorization": "Bearer test_token"})

    def test_send_request_network_error(self, client):
        client._session = MagicMock()
        client._session.request.side_effect = requests.RequestException("Network fail")

        with pytest.raises(MLAPIError, match="Network Error"):
            client._send_request("GET", "https://api.com/test")

    def test_create_session(self, client):
        session = client._create_session()
        assert isinstance(session, requests.Session)
        assert "https://" in session.adapters
        adapter = session.adapters["https://"]
        assert hasattr(adapter, "max_retries")
        assert adapter.max_retries.total == client.config.max_retries  # type: ignore[attr-defined]
        assert adapter.max_retries.backoff_factor == client.config.backoff_factor  # type: ignore[attr-defined]
        assert 429 in adapter.max_retries.status_forcelist  # type: ignore[attr-defined]
        assert session.headers["Accept"] == "application/json"
        assert session.headers["Content-Type"] == "application/json"


class TestMercadoLibreClientPublic:
    @patch.object(MercadoLibreClient, "_send_request")
    def test_request(self, mock_send, client):
        client.request("PATCH", "items/123", json={"foo": "bar"})
        mock_send.assert_called_once_with("PATCH", f"{client.config.base_url}/items/123", use_auth=True, json={"foo": "bar"})

    @patch.object(MercadoLibreClient, "_send_request")
    def test_exchange_code_for_token(self, mock_send, client):
        mock_send.return_value = {"access_token": "new_token"}

        result = client.exchange_code_for_token("some_code", "some_uri")

        assert result == {"access_token": "new_token"}
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert args == ("POST", f"{client.config.base_url}/oauth/token")
        assert kwargs["use_auth"] is False
        assert kwargs["json"]["code"] == "some_code"
        assert kwargs["json"]["grant_type"] == "authorization_code"

    @patch.object(MercadoLibreClient, "_send_request")
    def test_refresh_token(self, mock_send, client):
        mock_send.return_value = {"access_token": "refreshed_token"}

        result = client.refresh_token("refresh_token_value")

        assert result == {"access_token": "refreshed_token"}
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert args == ("POST", f"{client.config.base_url}/oauth/token")
        assert kwargs["json"]["refresh_token"] == "refresh_token_value"
        assert kwargs["json"]["grant_type"] == "refresh_token"

    @patch.object(MercadoLibreClient, "_send_request")
    def test_get(self, mock_send, client):
        client.get("items/123", params={"foo": "bar"})
        mock_send.assert_called_once_with("GET", f"{client.config.base_url}/items/123", use_auth=True, params={"foo": "bar"})

    @patch.object(MercadoLibreClient, "_send_request")
    def test_post(self, mock_send, client):
        client.post("items", json={"name": "test"})
        mock_send.assert_called_once_with("POST", f"{client.config.base_url}/items", use_auth=True, data=None, json={"name": "test"})

    @patch.object(MercadoLibreClient, "_send_request")
    def test_put(self, mock_send, client):
        client.put("items/123", json={"name": "updated"})
        mock_send.assert_called_once_with("PUT", f"{client.config.base_url}/items/123", use_auth=True, data=None, json={"name": "updated"})

    @patch.object(MercadoLibreClient, "_send_request")
    def test_delete(self, mock_send, client):
        client.delete("items/123")
        mock_send.assert_called_once_with("DELETE", f"{client.config.base_url}/items/123", use_auth=True)
