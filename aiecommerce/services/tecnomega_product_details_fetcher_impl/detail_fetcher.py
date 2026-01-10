import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from requests import Response

logger = logging.getLogger(__name__)


class TecnomegaDetailFetcher:
    """
    Resolves and fetches the canonical Tecnomega product detail page.

    Flow:
        1. Fetch search results page using SEARCH_URL_TEMPLATE
           (e.g., https://tecnomegastore.ec/searchi/1/{product_code})

        2. Locate the first product card <a> element

        3. Extract the canonical product URL:
           /product/<slug>?code=<product_code>

        4. Fetch and return the product detail HTML
    """

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.base_url = settings.TECNOMEGA_STORE_BASE_URL
        self.search_url_template = settings.TECNOMEGA_SEARCH_URL_TEMPLATE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_product_detail_html(self, product_code: str) -> str:
        """
        Returns the HTML of the canonical Tecnomega product page
        for the given distributor product code.
        """
        logger.info(
            "Resolving Tecnomega distributor page for product_code=%s",
            product_code,
        )

        search_html = self._fetch_search_results(product_code)
        product_url = self._extract_first_product_url(
            html=search_html,
            product_code=product_code,
        )

        logger.info("Resolved Tecnomega product URL: %s", product_url)

        return self._fetch_product_page(product_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_search_results(self, product_code: str) -> str:
        url = self.search_url_template.format(product_code=product_code)

        logger.debug("Fetching Tecnomega search page: %s", url)
        response = self._get(url)

        return response.text

    def _extract_first_product_url(self, html: str, product_code: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        """
        Product cards structure (simplified):

        <div class="flex flex-wrap pt-2">
            <div class="w-full ...">
                <div class="bg-white ...">
                    <a href="/product/...?...">
                        <div> <img> </div>
                        <p>Product name</p>
                    </a>
        """

        # Scope strictly to product grid area
        product_grid = soup.select_one("div.flex.flex-wrap.pt-2")
        if not product_grid:
            raise ValueError("Tecnomega product grid not found")

        product_links = product_grid.select("a[href^='/product/']")

        if not product_links:
            logger.error(
                "No Tecnomega product links found for code=%s",
                product_code,
            )
            raise ValueError(f"No Tecnomega product found for code={product_code}")

        if len(product_links) > 1:
            logger.warning(
                "Multiple Tecnomega results found for code=%s; using first",
                product_code,
            )

        relative_url = product_links[0].get("href")
        if not relative_url or not isinstance(relative_url, str):
            raise ValueError("Product link found without valid href string")

        return urljoin(self.base_url, relative_url)

    def _fetch_product_page(self, product_url: str) -> str:
        logger.debug("Fetching Tecnomega product page: %s", product_url)
        response = self._get(product_url)
        return response.text

    def _get(self, url: str) -> Response:
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            logger.exception("Failed fetching Tecnomega URL: %s", url)
            raise RuntimeError(f"Failed to fetch Tecnomega URL: {url}") from exc
