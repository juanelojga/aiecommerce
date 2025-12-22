import time
from typing import Any, List

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

# Adjust import according to your app structure
from aiecommerce.models.product import ProductRawWeb


class Command(BaseCommand):
    help = "Scrapes product data from tecnomega.com for specific categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scrape only the first 5 items per category and print to stdout.",
        )
        # NEW ARGUMENT: Accepts multiple categories
        parser.add_argument(
            "--categories",
            nargs="+",
            default=["notebook"],  # Default if nothing is provided
            help="List of categories/search terms to scrape (e.g. notebook monitor cpu)",
        )

    def handle(self, *args: Any, **options: Any):
        start_time = time.time()
        # Single session ID for the whole run
        scrape_session_id = f"tecnomega_{int(start_time)}"

        base_url: str = options.get("base_url") or getattr(settings, "STOCK_LIST_BASE_URL", "") or ""
        dry_run = options.get("dry_run")
        target_categories: List[str] = options.get("categories") or ["notebook"]

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        self.stdout.write(f"Starting Session: {scrape_session_id}")
        self.stdout.write(f"Categories to scrape: {', '.join(target_categories)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode."))

        # --- LOOP STARTS HERE ---
        for category in target_categories:
            self.stdout.write(self.style.MIGRATE_HEADING(f"--- Processing: {category} ---"))

            # Reset the list for this category
            products_to_create: List[ProductRawWeb] = []

            # Update params dynamically
            params = {
                "buscar": category,
            }

            try:
                response = requests.get(base_url, params=params, headers=headers, timeout=60)
                response.raise_for_status()
                response.encoding = "utf-8"
            except requests.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Failed to fetch category '{category}': {e}"))
                continue  # Skip to next category

            soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")

            product_table = soup.find("table", class_="table-hover")
            if not product_table:
                self.stderr.write(self.style.ERROR(f"No table found for category '{category}'"))
                continue

            tbody = product_table.find("tbody")
            if not tbody:
                rows = product_table.find_all("tr")
                rows = rows[1:] if len(rows) > 0 else []
            else:
                rows = tbody.find_all("tr")

            for row in rows:
                cols = row.find_all("td")

                if len(cols) < 10:
                    continue

                distributor_code = cols[0].get_text(strip=True)
                raw_description = cols[1].get_text(strip=True)
                stock_principal = cols[2].get_text(strip=True)
                stock_colon = cols[3].get_text(strip=True)
                stock_sur = cols[4].get_text(strip=True)
                stock_gye_norte = cols[5].get_text(strip=True)
                stock_gye_sur = cols[6].get_text(strip=True)

                image_tag = cols[9].find("img")
                image_url = image_tag.get("src", "") if image_tag else ""

                if not distributor_code:
                    continue

                if dry_run:
                    if len(products_to_create) < 5:
                        self.stdout.write(f"  [{category}] {distributor_code} - {raw_description[:30]}...")
                        products_to_create.append(
                            ProductRawWeb(distributor_code=distributor_code, raw_description=raw_description)
                        )
                    else:
                        break  # Stop parsing this category in dry run
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
                        search_term=category,  # <--- Saving the category here
                    )
                    products_to_create.append(product)

            # Save per category
            if not dry_run and products_to_create:
                try:
                    with transaction.atomic():
                        ProductRawWeb.objects.bulk_create(products_to_create, batch_size=100)
                    self.stdout.write(self.style.SUCCESS(f"Saved {len(products_to_create)} items for '{category}'"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error saving '{category}': {e}"))
            elif not products_to_create:
                self.stdout.write(self.style.WARNING(f"No items found for '{category}'"))

        self.stdout.write(self.style.SUCCESS(f"Run complete. Session ID: {scrape_session_id}"))
