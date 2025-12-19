import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aiecommerce.services.price_list_impl.exceptions import IngestionError
from aiecommerce.services.price_list_impl.repository import ProductRawRepository
from aiecommerce.services.price_list_impl.use_case import PriceListIngestionUseCase
from aiecommerce.services.price_list_ingestion import PriceListIngestionService


class Command(BaseCommand):
    help = "Fetches a price list from a URL, processes it, and loads it into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving any data to the database.",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            help="Optional override for the base URL to resolve the price list download link from.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        base_url = options.get("base_url") or getattr(settings, "PRICE_LIST_BASE_URL", "")

        if not base_url:
            raise CommandError("PRICE_LIST_BASE_URL is not set. Define it in your environment or use --base-url.")

        self.stdout.write(self.style.NOTICE(f"Starting price list ingestion from: {base_url}"))

        try:
            # Instantiate dependencies and the use case
            service = PriceListIngestionService()
            repo = ProductRawRepository()
            use_case = PriceListIngestionUseCase(service, repo)

            # Execute the use case
            result = use_case.execute(base_url, dry_run=dry_run)

            # Handle the output based on the result
            if result["status"] == "dry_run":
                self.stdout.write(self.style.SUCCESS("-- DRY RUN --"))
                self.stdout.write(f"Total items that would be ingested: {result['count']}")
                self.stdout.write("Showing first 5 items (preview):")
                self.stdout.write(json.dumps(result["preview"], indent=2, ensure_ascii=False))
                self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes were made."))
            elif result["status"] == "success":
                self.stdout.write(self.style.SUCCESS(f"Successfully ingested {result['count']} records."))

        except IngestionError as e:
            raise CommandError(f"An error occurred during ingestion: {e}")
        except Exception as e:
            raise CommandError(f"An unexpected error occurred: {e}")
