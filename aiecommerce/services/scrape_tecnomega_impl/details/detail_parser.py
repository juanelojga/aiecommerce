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
        # 1. Try original selector
        price_el = soup.select_one("p.text-amber-600")

        # 2. Try searching by label in the attribute-like rows
        if not price_el:
            rows = soup.select("div.flex.justify-between.border-b.border-slate-300")
            for row in rows:
                label_el = row.find("strong")
                if label_el and any(p in label_el.get_text().lower() for p in ["precio", "pvp"]):
                    price_el = row.find("span")
                    break

        if not price_el:
            # Last resort: search for any text that looks like a price near a "precio" label
            price_label = soup.find(string=re.compile(r"precio|pvp", re.I))
            if price_label:
                # Look for price in the parent or siblings
                parent = price_label.parent
                price_text = parent.get_text()
                match = re.search(r"([\d,.]+)", price_text)
                if match:
                    return float(match.group(1).replace(",", ""))

            # Try to find price in Next.js scripts
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and ("priceD" in script.string or "priceW" in script.string):
                    # Try to extract priceW (Wholesale/PVP) or priceD
                    match_w = re.search(r'\\?"priceW\\?":\s*([\d.]+)', script.string)
                    if match_w:
                        return float(match_w.group(1))
                    match_d = re.search(r'\\?"priceD\\?":\s*([\d.]+)', script.string)
                    if match_d:
                        return float(match_d.group(1))

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

        # Mapping of Spanish labels to English keys
        label_map = {
            "código": "sku",
            "marca": "brand",
            "linea": "line",
            "peso": "weight",
            "sku": "sku",
        }

        rows = soup.select("div.flex.justify-between.border-b.border-slate-300")

        for row in rows:
            label_el = row.find("strong")
            value_el = row.find("span")

            if not label_el or not value_el:
                continue

            label_text = label_el.get_text(strip=True).lower()
            value = value_el.get_text(strip=True)

            # Map the label to an English key if possible
            key = label_map.get(label_text, label_text)
            attributes[key] = value

        if not attributes:
            logger.warning("No attribute rows found on Tecnomega page")

        return attributes
