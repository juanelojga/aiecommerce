import logging

import requests
from requests import RequestException

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Handles downloading images with basic validation and error handling."""

    def __init__(self, timeout: int = 10, max_size_bytes: int = 10 * 1024 * 1024):
        self.timeout = timeout
        self.max_size_bytes = max_size_bytes

    def download(self, url: str) -> bytes | None:
        """
        Downloads an image from a URL with validation.
        """
        try:
            # Use stream=True to check content-type and size before downloading full payload
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                logger.warning(f"URL {url} did not return an image content type: {content_type}")
                return None

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_size_bytes:
                logger.warning(f"Image at {url} exceeds maximum size: {content_length} bytes")
                return None

            content = response.content
            if len(content) > self.max_size_bytes:
                logger.warning(f"Downloaded content from {url} exceeds maximum size.")
                return None

            return content
        except RequestException as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image from {url}: {e}")
            return None
