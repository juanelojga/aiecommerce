from unittest.mock import Mock, patch

import pytest
import requests

from aiecommerce.services.telegram_impl.telegram_service import TelegramNotificationService


@pytest.fixture
def mock_env_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up Telegram credentials in environment."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")


@pytest.fixture
def mock_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Telegram credentials from environment."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


class TestTelegramNotificationService:
    def test_is_configured_with_credentials(self, mock_env_credentials: None) -> None:
        """Test that service detects when credentials are configured."""
        service = TelegramNotificationService()
        assert service.is_configured() is True

    def test_is_configured_without_credentials(self, mock_no_credentials: None) -> None:
        """Test that service detects when credentials are missing."""
        service = TelegramNotificationService()
        assert service.is_configured() is False

    def test_init_logs_warning_without_credentials(self, mock_no_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test that initialization logs warning when credentials are missing."""
        TelegramNotificationService()
        assert "Telegram credentials not configured" in caplog.text

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_success(self, mock_post: Mock, mock_env_credentials: None) -> None:
        """Test successful message sending."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        service = TelegramNotificationService()
        result = service.send_message("Test message")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args.args[0] == "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
        assert call_args.kwargs["json"]["chat_id"] == "-1001234567890"
        assert call_args.kwargs["json"]["text"] == "Test message"
        assert call_args.kwargs["json"]["parse_mode"] == "HTML"

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_with_html_formatting(self, mock_post: Mock, mock_env_credentials: None) -> None:
        """Test that HTML formatting is properly sent."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        service = TelegramNotificationService()
        html_message = "<b>Bold</b> and <i>italic</i> text"
        result = service.send_message(html_message)

        assert result is True
        assert mock_post.call_args.kwargs["json"]["text"] == html_message
        assert mock_post.call_args.kwargs["json"]["parse_mode"] == "HTML"

    def test_send_message_without_credentials(self, mock_no_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test that sending fails gracefully without credentials."""
        service = TelegramNotificationService()
        result = service.send_message("Test message")

        assert result is False
        assert "credentials not configured" in caplog.text

    def test_send_message_empty_text(self, mock_env_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test that sending empty message returns False."""
        service = TelegramNotificationService()

        assert service.send_message("") is False
        assert service.send_message("   ") is False
        assert "Cannot send empty Telegram message" in caplog.text

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_request_exception(self, mock_post: Mock, mock_env_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test handling of network errors."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        service = TelegramNotificationService()
        result = service.send_message("Test message")

        assert result is False
        assert "Failed to send Telegram message" in caplog.text

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_http_error(self, mock_post: Mock, mock_env_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test handling of HTTP errors from Telegram API."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        service = TelegramNotificationService()
        result = service.send_message("Test message")

        assert result is False
        assert "Failed to send Telegram message" in caplog.text

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_unexpected_exception(self, mock_post: Mock, mock_env_credentials: None, caplog: pytest.LogCaptureFixture) -> None:
        """Test handling of unexpected exceptions."""
        mock_post.side_effect = Exception("Unexpected error")

        service = TelegramNotificationService()
        result = service.send_message("Test message")

        assert result is False
        assert "Unexpected error sending Telegram message" in caplog.text

    @patch("aiecommerce.services.telegram_impl.telegram_service.requests.post")
    def test_send_message_timeout(self, mock_post: Mock, mock_env_credentials: None) -> None:
        """Test that timeout is set on HTTP request."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        service = TelegramNotificationService()
        service.send_message("Test message")

        assert mock_post.call_args.kwargs["timeout"] == 10
