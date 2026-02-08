import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Service for sending notifications via Telegram Bot API."""

    def __init__(self) -> None:
        """Initialize the Telegram notification service with credentials from environment."""
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.base_url = "https://api.telegram.org"

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")

    def is_configured(self) -> bool:
        """Check if Telegram credentials are properly configured."""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str) -> bool:
        """
        Send a text message to the configured Telegram chat.

        Args:
            text: The message text to send (supports HTML formatting)

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Cannot send Telegram message: credentials not configured")
            return False

        if not text or not text.strip():
            logger.warning("Cannot send empty Telegram message")
            return False

        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Telegram message sent successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False
