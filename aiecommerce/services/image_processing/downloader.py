import logging

import requests
from requests import RequestException

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Handles downloading images with basic validation and error handling."""

    def __init__(self, timeout: int = 10, max_size_bytes: int = 10 * 1024 * 1024):
        """Initialize the downloader with timeout and size limits.

        Args:
            timeout: Maximum seconds to wait for download.
            max_size_bytes: Maximum allowed image size in bytes.
        """
        self.timeout = timeout
        self.max_size_bytes = max_size_bytes

    def download(self, url: str) -> bytes | None:
        """Download an image from a URL with validation.

        Args:
            url: The image URL to download.

        Returns:
            The image bytes if successful, None otherwise.
        """
        try:
            # Use stream=True to check content-type and size before downloading full payload
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

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
