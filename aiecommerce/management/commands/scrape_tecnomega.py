import time

# ... necessary imports ...
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

# Adjust import according to your app structure
from aiecommerce.models.product import ProductRawWeb


class Command(BaseCommand):
    help = "Scrapes product data from tecnomega.com and saves it to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scrape only the first 5 items and print to stdout without saving.",
        )

    def handle(self, *args: Any, **options: Any):
        start_time = time.time()
        # Use a timestamp for the session ID
        scrape_session_id = f"tecnomega_{int(start_time)}"

        base_url = "https://buscador.tecnomega.com/"
        # Note: Ensure the URL is correct (your snippet had 'busqueda.php' right after base_url)
        search_url: Optional[str] = f"{base_url}busqueda.php?ico=&buscar=notebook"

        dry_run = options["dry_run"]

        # Add headers to look like a real browser (prevents some blocking)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        self.stdout.write(f"Starting scrape session: {scrape_session_id}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in --dry-run mode. Data will not be saved."))

        products_to_create: List[ProductRawWeb] = []  # Fix type annotation
        page_count = 1

        while search_url:
            self.stdout.write(f"Scraping page {page_count}: {search_url}")
            try:
                response = requests.get(search_url, headers=headers, timeout=60)
                response.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Failed to fetch {search_url}: {e}"))
                break

            soup = BeautifulSoup(response.content, "html.parser")

            # --- FIX 1: Updated Selector to match your HTML classes ---
            # We look for the table that has 'table-hover' class
            product_table = soup.find("table", class_="table-hover")

            if not product_table:
                self.stderr.write(self.style.ERROR("Could not find the product table on the page."))
                # Debug: print a bit of the HTML to see what we actually got
                # self.stdout.write(soup.prettify()[:1000])
                break

            # --- FIX 2: Target tbody specifically ---
            tbody = product_table.find("tbody")
            if not tbody:
                # Fallback if tbody is missing (some browsers add it, raw html might not have it)
                rows = product_table.find_all("tr")
                # Skip header if grabbing from main table
                rows = rows[1:] if len(rows) > 0 else []
            else:
                rows = tbody.find_all("tr")

            for row in rows:
                cols = row.find_all("td")

                # --- FIX 3: Validation based on your 11 columns ---
                # HTML has approx 10-11 columns. We need at least up to the Image column.
                if len(cols) < 10:
                    continue

                # --- FIX 4: Correct Column Mapping ---
                # Col 0: Código
                distributor_code = cols[0].get_text(strip=True)

                # Col 1: Descripción
                raw_description = cols[1].get_text(strip=True)

                # Col 2: Principal
                stock_principal = cols[2].get_text(strip=True)

                # Col 3: Colón
                stock_colon = cols[3].get_text(strip=True)

                # Col 4: Sur
                stock_sur = cols[4].get_text(strip=True)

                # Col 5: Gye Norte
                stock_gye_norte = cols[5].get_text(strip=True)

                # Col 6: Gye Sur (Your previous code missed this)
                stock_gye_sur = cols[6].get_text(strip=True)

                # Col 9: Imagen (Usually the last column in your screenshot)
                # The image is usually inside an <a> tag or directly in td
                image_tag = cols[9].find("img")
                image_url = image_tag.get("src", "") if image_tag else ""

                if not distributor_code:
                    continue

                if dry_run:
                    if len(products_to_create) < 5:
                        self.stdout.write(
                            f"  - Code: {distributor_code}\n"
                            f"    Desc: {raw_description[:40]}...\n"
                            f"    Stock (P/C/S): {stock_principal}/{stock_colon}/{stock_sur}\n"
                            f"    Img: {image_url}"
                        )
                        # Use ProductRawWeb instance to meet type requirement
                        products_to_create.append(
                            ProductRawWeb(distributor_code=distributor_code, raw_description=raw_description)
                        )
                    else:
                        break
                else:
                    product = ProductRawWeb(
                        distributor_code=distributor_code,
                        raw_description=raw_description,
                        stock_principal=stock_principal,
                        stock_colon=stock_colon,
                        stock_sur=stock_sur,
                        stock_gye_norte=stock_gye_norte,
                        stock_gye_sur=stock_gye_sur,
                        image_url=image_url,
                        scrape_session_id=scrape_session_id,
                    )
                    products_to_create.append(product)

            # Pagination logic
            next_page_link = soup.find("a", string=lambda t: t and ("Siguiente" in t or ">" in t))
            search_url = (
                f"{base_url}{next_page_link['href']}" if next_page_link and next_page_link.get("href") else None
            )

        # Final database save
        if not dry_run and products_to_create:
            self.stdout.write(f"Found {len(products_to_create)} products. Saving to database...")
            try:
                with transaction.atomic():
                    ProductRawWeb.objects.bulk_create(products_to_create, batch_size=100)
                self.stdout.write(self.style.SUCCESS("Successfully saved all products."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred during bulk insert: {e}"))
