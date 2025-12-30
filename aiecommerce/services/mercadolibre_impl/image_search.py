import logging
from typing import List

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class ImageSearchService:
    """
    A service to find product images using Google Custom Search API.
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.search_engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        if not self.api_key or not self.search_engine_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set in settings.")
        self.service = build("customsearch", "v1", developerKey=self.api_key)

    def find_image_urls(self, query: str) -> List[str]:
        """
        Finds the URLs of up to 5 'huge' 'photo' image results for a given query.

        Args:
            query: The search term for the image.

        Returns:
            A list of image URLs, or an empty list if no suitable images are found
            or an error occurs.
        """
        logger.info(f"Searching for up to 5 images with query: '{query}'")
        try:
            result = (
                self.service.cse()
                .list(
                    q=query,
                    cx=self.search_engine_id,
                    searchType="image",
                    imgSize="huge",
                    imgType="photo",
                    num=5,
                )
                .execute()
            )

            items = result.get("items", [])
            if not items:
                logger.warning(f"No image results found for query: '{query}'")
                return []

            image_urls = [item.get("link") for item in items if item.get("link")]
            logger.info(f"Found {len(image_urls)} image URLs for '{query}'")
            return image_urls

        except HttpError as e:
            logger.error(f"HTTP error occurred while searching for images for '{query}': {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred while searching for images for '{query}': {e}", exc_info=True)
            return []
