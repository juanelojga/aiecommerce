import logging
import re
from typing import Dict, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TecnomegaDetailParser:
    """
    Parses a Tecnomega product detail page HTML and extracts
    structured product data.
    """

    CURRENCY = "USD"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, html: str) -> Dict:
        soup = BeautifulSoup(html, "html.parser")

        return {
            "name": self._parse_name(soup),
            "price": self._parse_price(soup),
            "currency": self.CURRENCY,
            "images": self._parse_images(soup),
            "attributes": self._parse_attributes(soup),
        }

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------

    def _parse_name(self, soup: BeautifulSoup) -> str:
        h1 = soup.select_one("div.md\\:w-2\\/6 h1")
        if not h1:
            raise ValueError("Product name (h1) not found")

        return h1.get_text(strip=True)

    def _parse_price(self, soup: BeautifulSoup) -> float:
        price_el = soup.select_one("p.text-amber-600")
        if not price_el:
            raise ValueError("Product price not found")

        price_text = price_el.get_text(strip=True)

        # Example: "$1573.78"
        match = re.search(r"([\d,.]+)", price_text)
        if not match:
            raise ValueError(f"Unable to parse price from '{price_text}'")

        return float(match.group(1).replace(",", ""))

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def _parse_images(self, soup: BeautifulSoup) -> List[str]:
        images: List[str] = []

        # Main image (large preview)
        main_img = soup.select_one("div.flex.justify-center img[alt='image-current']")
        if main_img and main_img.get("src"):
            main_src = main_img["src"]
            if isinstance(main_src, str):
                images.append(main_src)

        # Thumbnails
        thumbnails = soup.select("div.bg-zinc-100 img[src]")
        for img in thumbnails:
            thumb_src = img.get("src")
            if isinstance(thumb_src, str) and thumb_src not in images:
                images.append(thumb_src)

        if not images:
            logger.warning("No images found on Tecnomega product page")

        return images

    # ------------------------------------------------------------------
    # Attributes (Código, Marca, Linea, Peso, Sku)
    # ------------------------------------------------------------------

    def _parse_attributes(self, soup: BeautifulSoup) -> Dict[str, str]:
        attributes: Dict[str, str] = {}

        rows = soup.select("div.flex.justify-between.border-b.border-slate-300")

        for row in rows:
            label_el = row.find("strong")
            value_el = row.find("span")

            if not label_el or not value_el:
                continue

            label = label_el.get_text(strip=True).lower()
            value = value_el.get_text(strip=True)

            attributes[label] = value

        if not attributes:
            logger.warning("No attribute rows found on Tecnomega page")

        return attributes
