import logging

from celery import shared_task

from aiecommerce.services.telegram_impl import TelegramNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_telegram_notification(self, message: str) -> bool:
    """
    Send a Telegram notification asynchronously via Celery.

    This task will automatically retry up to 3 times with a 60-second delay
    between retries if the notification fails to send.

    Args:
        message: The text message to send (supports HTML formatting)

    Returns:
        True if the message was sent successfully, False otherwise
    """
    try:
        service = TelegramNotificationService()

        if not service.is_configured():
            logger.warning("Telegram notification skipped: credentials not configured")
            return False

        success = service.send_message(message)

        if not success and self.request.retries < self.max_retries:
            logger.warning(f"Telegram notification failed, retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry()

        return success

    except Exception as e:
        logger.error(f"Failed to send Telegram notification after retries: {e}")
        return False
