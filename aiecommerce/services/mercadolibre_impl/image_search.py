import logging
import re
from typing import List
from urllib.parse import urlparse

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aiecommerce.models.product import ProductMaster

logger = logging.getLogger(__name__)


class ImageCandidateSelector:
    """
    A service to select product candidates for image processing.
    """

    def find_products_without_images(self) -> List[ProductMaster]:
        """
        Finds products that are active, destined for Mercado Libre, and have no associated images.

        Returns:
            A list of ProductMaster instances.
        """
        return list(
            ProductMaster.objects.filter(
                is_active=True,
                is_for_mercadolibre=True,
                images__isnull=True,
            )
        )


class ImageSearchService:
    """
    A service to find product images using Google Custom Search API.
    """

    DOMAIN_BLOCKLIST = {
        # Social Media
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "pinterest.com",
        "linkedin.com",
        "reddit.com",
        # E-commerce sites that are often not the source
        "amazon.com",
        "ebay.com",
        "aliexpress.com",
        "walmart.com",
        # Stock photos
        "istockphoto.com",
        "shutterstock.com",
        "gettyimages.com",
        "pexels.com",
        "unsplash.com",
        # Other
        "wikipedia.org",
        "wikimedia.org",
    }

    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_API_KEY
        self.search_engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        if not self.api_key or not self.search_engine_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set in settings.")
        self.service = build("customsearch", "v1", developerKey=self.api_key)

    def find_image_urls(self, query: str, count: int = 5) -> List[str]:
        """
        Finds the URLs of up to a specified count of 'huge' or 'large' 'photo' image results for a given query,
        filtering out low-quality domains.

        Args:
            query: The search term for the image.
            count: The maximum number of image URLs to return.

        Returns:
            A list of unique image URLs, or an empty list if no suitable images are found or an error occurs.
        """
        logger.info(f"Searching for up to {count} images with query: '{query}'")
        try:
            result = (
                self.service.cse()
                .list(
                    q=query,
                    cx=self.search_engine_id,
                    searchType="image",
                    imgSize="huge",  # API also supports 'large', 'xlarge', etc.
                    num=count,
                )
                .execute()
            )

            items = result.get("items", [])
            if not items:
                logger.warning(f"No image results found for query: '{query}'")
                return []

            image_urls = []
            for item in items:
                if link := item.get("link"):
                    domain = urlparse(link).netloc
                    if domain not in self.DOMAIN_BLOCKLIST:
                        image_urls.append(link)

            unique_image_urls = list(dict.fromkeys(image_urls))[:count]  # Remove duplicates and respect count

            logger.info(f"Found {len(unique_image_urls)} unique image URLs for '{query}' after filtering.")
            return unique_image_urls

        except HttpError as e:
            logger.error(f"HTTP error occurred while searching for images for '{query}': {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred while searching for images for '{query}': {e}", exc_info=True)
            return []

    def build_search_query(self, product: ProductMaster) -> str:
        """
        Constructs a professional product image search query.
        Extracts 'brand', 'model', and 'category' from product.specs.
        Fall back to product.description if specs are missing.
        Constructs a query string like: '[Brand] [Model] [Category] official product image white background'.
        Cleans the string to remove any special characters that might break a search.

        Args:
            product: The ProductMaster instance.

        Returns:
            The cleaned search query string.
        """
        brand = product.specs.get("brand") if product.specs else None
        model = product.specs.get("model") if product.specs else None
        category = product.specs.get("category") if product.specs else None

        query_parts = []
        if brand:
            query_parts.append(str(brand))
        if model:
            query_parts.append(str(model))
        if category:
            query_parts.append(str(category))

        if product.description:
            query_parts.append(product.description)

        base_query = " ".join(query_parts)
        final_query = f"{base_query} official product image white background"

        # Clean the string to remove any special characters that might break a search
        cleaned_query = re.sub(r"[^\w\s]", "", final_query).strip()
        return cleaned_query
