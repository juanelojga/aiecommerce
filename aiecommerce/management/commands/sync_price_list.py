import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from aiecommerce.models import ProductRawPDF
from aiecommerce.services.price_list_ingestion import PriceListIngestionService


class Command(BaseCommand):
    help = "Fetches a price list from a URL, processes it, and loads it into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving any data to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        # Use a dummy URL or an environment variable.
        # For this example, a placeholder is used.
        # In a real application, this should be fetched from settings or env.
        url = os.environ.get("PRICE_LIST_URL", "https://example.com/dummy-price-list.xls")

        self.stdout.write(self.style.NOTICE(f"Starting price list ingestion from {url}..."))

        ingestion_service = PriceListIngestionService()
        file_content = ingestion_service.fetch(url)
        if not file_content:
            self.stdout.write(self.style.WARNING("Failed to download price list. Exiting."))
            return
        parsed_data = ingestion_service.parse(file_content)

        if not parsed_data:
            self.stdout.write(self.style.WARNING("No data was parsed from the URL. Exiting."))
            return

        total_items = len(parsed_data)
        self.stdout.write(f"Found {total_items} items to process.")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("-- DRY RUN --"))
            self.stdout.write(f"Total items that would be ingested: {total_items}")
            self.stdout.write("Showing first 5 items:")
            for item in parsed_data[:1000]:
                self.stdout.write(str(item))
            self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes were made."))
            return

        # --- Live Mode ---
        self.stdout.write(self.style.NOTICE("Executing live run. Database will be modified."))

        try:
            # 1. Truncate the table
            self.stdout.write(f"Deleting all {ProductRawPDF.objects.count()} existing records...")
            ProductRawPDF.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Successfully cleared ProductRawPDF table."))

            # 2. Prepare data for bulk creation
            now = datetime.now()
            products_to_create = [
                ProductRawPDF(
                    raw_description=item.get("raw_description"),
                    distributor_price=item.get("distributor_price"),
                    category_header=item.get("category_header"),
                    created_at=now,
                )
                for item in parsed_data
            ]

            # 3. Load data using bulk_create
            self.stdout.write(f"Inserting {len(products_to_create)} new records in batches...")
            ProductRawPDF.objects.bulk_create(products_to_create, batch_size=1000)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully ingested {len(products_to_create)} records into ProductRawPDF.")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred during the database operation: {e}"))
            self.stdout.write(self.style.WARNING("Transaction rolled back. No data was committed."))
