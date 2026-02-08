from unittest.mock import Mock, patch

import pytest

from aiecommerce.tasks.notifications import send_telegram_notification


@pytest.fixture
def mock_telegram_service() -> Mock:
    """Create a mock TelegramNotificationService."""
    service = Mock()
    service.is_configured.return_value = True
    service.send_message.return_value = True
    return service


class TestSendTelegramNotification:
    @patch("aiecommerce.tasks.notifications.TelegramNotificationService")
    def test_send_notification_success(self, mock_service_class: Mock, mock_telegram_service: Mock) -> None:
        """Test successful notification sending."""
        mock_service_class.return_value = mock_telegram_service

        result = send_telegram_notification("Test message")

        assert result is True
        mock_telegram_service.send_message.assert_called_once_with("Test message")

    @patch("aiecommerce.tasks.notifications.TelegramNotificationService")
    def test_send_notification_not_configured(self, mock_service_class: Mock, mock_telegram_service: Mock, caplog: pytest.LogCaptureFixture) -> None:
        """Test that notification is skipped when credentials not configured."""
        mock_telegram_service.is_configured.return_value = False
        mock_service_class.return_value = mock_telegram_service

        result = send_telegram_notification("Test message")

        assert result is False
        assert "credentials not configured" in caplog.text
        mock_telegram_service.send_message.assert_not_called()

    @patch("aiecommerce.tasks.notifications.TelegramNotificationService")
    def test_send_notification_html_formatting(self, mock_service_class: Mock, mock_telegram_service: Mock) -> None:
        """Test that HTML formatted messages are passed through."""
        mock_service_class.return_value = mock_telegram_service
        html_message = "<b>Bold</b> text"

        result = send_telegram_notification(html_message)

        assert result is True
        mock_telegram_service.send_message.assert_called_once_with(html_message)

    @patch("aiecommerce.tasks.notifications.TelegramNotificationService")
    def test_send_notification_service_failure(self, mock_service_class: Mock, mock_telegram_service: Mock) -> None:
        """Test handling when service returns False."""
        mock_telegram_service.send_message.return_value = False
        mock_service_class.return_value = mock_telegram_service

        result = send_telegram_notification("Test message")

        assert result is False

    @patch("aiecommerce.tasks.notifications.TelegramNotificationService")
    def test_send_notification_exception_handling(self, mock_service_class: Mock, caplog: pytest.LogCaptureFixture) -> None:
        """Test that exceptions are caught and logged."""
        mock_service_class.side_effect = Exception("Unexpected error")

        result = send_telegram_notification("Test message")

        assert result is False
        assert "Failed to send Telegram notification" in caplog.text
