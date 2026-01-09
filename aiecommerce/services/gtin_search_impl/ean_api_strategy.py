from typing import Any, Dict, Iterable, List, Optional

from django.core.cache import cache

from aiecommerce.models import ProductMaster

from .ean_search_client import EANSearchClient
from .matcher import ProductMatcher

APIResult = Dict[str, Any]


class EANSearchAPIStrategy:
    """
    Implements a GTIN search strategy using an EAN search API.
    Features:
    - Caches raw API responses for queries for 7 days.
    - Uses a 'Model Name first, SKU fallback' query logic.
    - Employs a 'Golden Match' early exit for high-confidence results.
    - Falls back to the best candidate above a certain threshold.
    """

    # Constants for matching thresholds
    GOLDEN_MATCH_THRESHOLD = 0.95
    MINIMUM_CANDIDATE_THRESHOLD = 0.75

    def __init__(self, client: EANSearchClient, matcher: ProductMatcher):
        self.client = client
        self.matcher = matcher

    def search_for_gtin(self, product: ProductMaster) -> Optional[str]:
        """
        Searches for a GTIN for the given product.

        First, it attempts to find a result based on the product's model name.
        If that yields no match, it falls back to searching by SKU.

        Args:
            product: The ProductMaster instance to search for.

        Returns:
            The found GTIN as a string, or None if no suitable match is found.
        """
        # 1. 'Model Name first'
        query = self._get_query(product, use_sku=False)
        if query:
            gtin = self._execute_search(product, query)
            if gtin:
                return gtin

        # 2. 'SKU fallback'
        query = self._get_query(product, use_sku=True)
        if query:
            gtin = self._execute_search(product, query)
            if gtin:
                return gtin

        return None

    def _execute_search(self, product: ProductMaster, query: str) -> Optional[str]:
        """
        Manages caching and initiates the result processing for a given query.
        """
        cache_key = self._get_cache_key(query)
        cached_results = cache.get(cache_key)

        if cached_results:
            results_iterable = cached_results
            is_live_search = False
        else:
            results_iterable = self.client.search(query)
            is_live_search = True

        return self._process_results(product, results_iterable, is_live_search, cache_key)

    def _get_query(self, product: ProductMaster, use_sku: bool = False) -> Optional[str]:
        """Determines the search query."""
        if use_sku:
            return product.sku
        if product.model_name and len(product.model_name) > 2:
            return product.model_name
        return None

    def _get_cache_key(self, query: str) -> str:
        """Generates a cache key for a given search query."""
        return f"gtin_search:ean_api:{query.lower().replace(' ', '_')}"

    def _process_results(self, product: ProductMaster, results: Iterable[APIResult], is_live_search: bool, cache_key: str) -> Optional[str]:
        """
        Iterates through search results to find the best GTIN match.
        - On a live search, it stops immediately if a Golden Match is found.
        - If no golden match is found after checking all results, it caches the full list.
        - Finally, it returns the best candidate that meets the minimum threshold.
        """
        best_candidate_gtin: Optional[str] = None
        best_score = 0.0
        processed_results_for_cache: List[APIResult] = []

        for result in results:
            if is_live_search:
                processed_results_for_cache.append(result)

            score = self.matcher.calculate_confidence(result.get("name", ""), product.specs or {})

            if score > self.GOLDEN_MATCH_THRESHOLD:
                # Golden Match found, stop immediately and return.
                return result.get("gtin")

            if score > best_score:
                best_score = score
                best_candidate_gtin = result.get("gtin")

        # Loop finished. If it was a live search that didn't find a golden match, cache results.
        if is_live_search and processed_results_for_cache:
            cache.set(cache_key, processed_results_for_cache, timeout=7 * 24 * 60 * 60)

        # If no Golden Match was found, return the best candidate if it's good enough.
        if best_score > self.MINIMUM_CANDIDATE_THRESHOLD:
            return best_candidate_gtin

        return None
