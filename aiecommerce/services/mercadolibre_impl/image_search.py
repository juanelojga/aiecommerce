import logging
import re
from typing import Any, List, Optional, Protocol, Set
from urllib.parse import urlparse

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aiecommerce.models.product import ProductMaster

logger = logging.getLogger(__name__)


class GoogleSearchClient(Protocol):
    """Protocol for Google Custom Search API client."""

    def list(self, **kwargs: Any) -> Any: ...


class ImageCandidateSelector:
    """
    A service to select product candidates for image processing.
    """

    def find_products_without_images(self, limit: Optional[int] = None) -> Any:
        """
        Finds products that are active, destined for Mercado Libre, and have no associated images.

        Returns:
            A QuerySet of ProductMaster instances.
        """
        qs = ProductMaster.objects.filter(
            is_active=True,
            is_for_mercadolibre=True,
            images__isnull=True,
        ).distinct()
        if limit:
            qs = qs[:limit]
        return qs


class QueryConstructor:
    """Handles the logic for building search queries from product data."""

    DEFAULT_NOISY_TERMS: str = r"\b(Cop|Si|No|Precio|Stock|Garantia|3yb|W11pro)\b"
    DEFAULT_QUERY_SUFFIX: str = "official product image white background"

    def __init__(
        self,
        noisy_terms: Optional[str] = None,
        query_suffix: Optional[str] = None,
    ):
        # Initialize with defaults
        self.noisy_terms: str = self.DEFAULT_NOISY_TERMS
        self.query_suffix: str = self.DEFAULT_QUERY_SUFFIX

        # Try to get from arguments or settings
        val_noisy = noisy_terms or getattr(settings, "IMAGE_SEARCH_NOISY_TERMS", self.DEFAULT_NOISY_TERMS)
        val_suffix = query_suffix or getattr(settings, "IMAGE_SEARCH_QUERY_SUFFIX", self.DEFAULT_QUERY_SUFFIX)

        # Ensure we have strings (especially if settings are mocked)
        if isinstance(val_noisy, str):
            self.noisy_terms = val_noisy
        if isinstance(val_suffix, str):
            self.query_suffix = val_suffix

    def build_query(self, product: ProductMaster) -> str:
        """Constructs a precise query by prioritizing Brand/Model over raw description."""
        specs = product.specs or {}
        brand = specs.get("brand", "")
        model = specs.get("model", "")
        category = specs.get("category", "")

        if brand and model:
            base_query = f"{brand} {model} {category}"
        else:
            clean_desc = re.sub(self.noisy_terms, "", product.description or "", flags=re.IGNORECASE)
            base_query = " ".join(clean_desc.split()[:6])

        final_query = f"{base_query} {self.query_suffix}"
        cleaned = re.sub(r"[^\w\s]", "", final_query).strip()
        return " ".join(cleaned.split())[:100].strip()


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
                result = (
                    self.service.cse()
                    .list(q=query, cx=self.search_engine_id, searchType="image", imgSize="HUGE", num=num_to_fetch, start=start_index)
                    .execute()
                )

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
