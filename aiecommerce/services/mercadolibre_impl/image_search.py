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
    NOISY_TERMS = {"cop", "si", "no", "precio"}

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
                    imgSize="HUGE",  # API also supports 'large', 'xlarge', etc.
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
        Constructs a robust search query for finding product images.

        - Prioritizes 'brand' and 'model' from product specs if available.
        - Falls back to the first 5 non-noisy words from the product description.
        - Appends 'official product image' for better results.
        - Cleans and truncates the query to a maximum of 100 characters.

        Args:
            product: The ProductMaster instance.

        Returns:
            A clean and effective search query string.
        """
        brand = product.specs.get("brand") if product.specs else None
        model = product.specs.get("model") if product.specs else None
        category = product.specs.get("category") if product.specs else None

        base_query = ""
        if brand and model:
            query_parts = [str(brand), str(model)]
            if category:
                query_parts.append(str(category))
            query_parts.append("official product image")
            base_query = " ".join(query_parts)
        elif product.description:
            # Clean description and then split into words
            cleaned_description = re.sub(r"[^\w\s]", "", product.description)
            description_words = cleaned_description.split()
            filtered_words = [word for word in description_words if word.lower() not in self.NOISY_TERMS][:5]
            base_query = " ".join(filtered_words)

        # Final clean and truncate
        cleaned_query = re.sub(r"[^\w\s]", "", base_query).strip()
        return cleaned_query[:100]
