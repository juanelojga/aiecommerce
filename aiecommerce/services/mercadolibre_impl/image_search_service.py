import logging
from typing import Any, List, Optional, Set
from urllib.parse import urlparse

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aiecommerce.models.product import ProductMaster

from .query_constructor import QueryConstructor

logger = logging.getLogger(__name__)


class ImageSearchService:
    """
    A service to find product images using Google Custom Search API.
    """

    DEFAULT_DOMAIN_BLOCKLIST = {
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "pinterest.com",
        "linkedin.com",
        "reddit.com",
        "amazon.com",
        "ebay.com",
        "aliexpress.com",
        "walmart.com",
        "istockphoto.com",
        "shutterstock.com",
        "gettyimages.com",
        "pexels.com",
        "unsplash.com",
        "wikipedia.org",
        "wikimedia.org",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
        service: Optional[Any] = None,
        domain_blocklist: Optional[Set[str]] = None,
        query_constructor: Optional[QueryConstructor] = None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "GOOGLE_API_KEY", None)
        self.search_engine_id = search_engine_id or getattr(settings, "GOOGLE_SEARCH_ENGINE_ID", None)

        if not self.api_key or not self.search_engine_id:
            logger.error("GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be configured.")
            raise ValueError("API credentials missing.")

        # If service is provided, use it. Otherwise build it.
        if service:
            self.service = service
        else:
            self.service = build("customsearch", "v1", developerKey=self.api_key)

        self.domain_blocklist = domain_blocklist if domain_blocklist is not None else self.DEFAULT_DOMAIN_BLOCKLIST
        self.query_constructor = query_constructor or QueryConstructor()

    def _is_blocked(self, url: str) -> bool:
        """Checks if a URL belongs to a blocked domain or its subdomains."""
        domain = urlparse(url).netloc.lower()
        if not domain:
            return True

        for blocked in self.domain_blocklist:
            if domain == blocked or domain.endswith("." + blocked):
                return True
        return False

    def find_image_urls(self, query: str, image_search_count: Optional[int] = None) -> List[str]:
        """
        Finds the URLs of image results for a given query, filtering out low-quality domains.
        Supports pagination for counts > 10.
        """
        if image_search_count is None:
            image_search_count = getattr(settings, "IMAGE_SEARCH_COUNT", 10)

        logger.info(f"Searching for up to {image_search_count} images with query: '{query}'")

        image_urls: List[str] = []
        start_index = 1

        # Google Custom Search API 'start' parameter max value is usually around 100
        while len(image_urls) < image_search_count and start_index <= 100:
            num_to_fetch = min(image_search_count - len(image_urls), 10)

            try:
                result = self.service.cse().list(q=query, cx=self.search_engine_id, searchType="image", imgSize="HUGE", num=num_to_fetch, start=start_index).execute()

                items = result.get("items", [])
                if not items:
                    if not image_urls:
                        logger.warning(f"No image results found for query: '{query}'")
                    break

                for item in items:
                    if link := item.get("link"):
                        if not self._is_blocked(link):
                            image_urls.append(link)

                if "nextPage" not in result.get("queries", {}):
                    break

                # Update start_index based on nextPage if available, otherwise just increment by 10
                next_page = result.get("queries", {}).get("nextPage", [{}])[0]
                start_index = next_page.get("startIndex", start_index + 10)

            except HttpError as e:
                logger.error(f"HTTP error occurred while searching for images for '{query}': {e}", exc_info=True)
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred while searching for images for '{query}': {e}", exc_info=True)
                break

        unique_urls = list(dict.fromkeys(image_urls))[:image_search_count]
        logger.info(f"Found {len(unique_urls)} unique image URLs for '{query}' after filtering.")
        return unique_urls

    def build_search_query(self, product: ProductMaster) -> str:
        """Delegates query construction to QueryConstructor."""
        return self.query_constructor.build_query(product)
