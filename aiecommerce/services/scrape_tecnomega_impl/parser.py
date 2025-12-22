# --- services/scrape_tecnomega_impl/parser.py ---
import logging
from typing import Dict, List, Optional, cast

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HtmlParser:
    """Parses HTML content to extract raw product data from a table."""

    # Expected number of columns in the product table
    EXPECTED_COLUMN_COUNT = 10

    def parse(self, html_content: str) -> List[Dict[str, Optional[str]]]:
        """
        Parses the HTML content to find the product table and extract data.

        Args:
            html_content: The HTML content of the page.

        Returns:
            A list of dictionaries, where each dictionary represents a raw product row.
        """
        logger.info("Starting HTML parsing.")
        soup = BeautifulSoup(html_content, "html.parser")

        product_table = soup.find("table", class_="table-hover")
        if not product_table:
            logger.warning("No product table with class 'table-hover' found.")
            return []

        # Validate header (optional but good practice)
        header = product_table.find("thead")
        if header:
            header_cols = header.find_all("th")
            if len(header_cols) < self.EXPECTED_COLUMN_COUNT:
                logger.warning(
                    f"Table header has {len(header_cols)} columns, "
                    f"expected at least {self.EXPECTED_COLUMN_COUNT}. Parsing may be incorrect."
                )

        # Find all rows in the table body
        tbody = product_table.find("tbody")
        rows = tbody.find_all("tr") if tbody else []
        if not rows:
            logger.info("No rows found in table body.")
            return []

        logger.info(f"Found {len(rows)} rows to process.")
        raw_products = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < self.EXPECTED_COLUMN_COUNT:
                logger.debug(f"Skipping row with {len(cols)} columns.")
                continue

            # Extract data based on column position
            image_tag = cols[9].find("img")
            row_data = {
                "distributor_code": cols[0].get_text(strip=True),
                "raw_description": cols[1].get_text(strip=True),
                "stock_principal": cols[2].get_text(strip=True),
                "stock_colon": cols[3].get_text(strip=True),
                "stock_sur": cols[4].get_text(strip=True),
                "stock_gye_norte": cols[5].get_text(strip=True),
                "stock_gye_sur": cols[6].get_text(strip=True),
                # BeautifulSoup may return AttributeValueList for src; cast to Optional[str] for typing
                "image_url": cast(Optional[str], image_tag.get("src")) if image_tag else None,
            }

            # A row must have at least a distributor code to be valid
            if row_data["distributor_code"]:
                raw_products.append(row_data)
            else:
                logger.debug("Skipping row with no distributor code.")

        logger.info(f"Successfully parsed {len(raw_products)} valid product rows.")
        return raw_products
