import logging
from typing import Any, Dict

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.scrape_tecnomega_impl.detail_fetcher import (
    TecnomegaDetailFetcher,
)
from aiecommerce.services.scrape_tecnomega_impl.detail_orchestrator import (
    TecnomegaDetailOrchestrator,
)
from aiecommerce.services.scrape_tecnomega_impl.detail_parser import (
    TecnomegaDetailParser,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to execute the TecnomegaDetailOrchestrator for a single product.
    """

    help = "Fetches and syncs detailed product information from Tecnomega for a given product code."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("product_code", type=str, help="The product code (ProductMaster.code) to sync.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Prevents any database persistence. Prints the parsed data to the console instead.",
        )
        parser.add_argument(
            "--no-dry-run",
            action="store_false",
            dest="dry_run",
            help="Disables dry-run mode, allowing database persistence.",
        )

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        product_code = options["product_code"]
        dry_run = options["dry_run"]

        self.stdout.write(self.style.NOTICE(f"Starting detail sync for product code: {product_code}"))

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f"ProductMaster with code '{product_code}' not found.")

        orchestrator = TecnomegaDetailOrchestrator()

        if dry_run:
            self.stdout.write(self.style.WARNING("-- DRY RUN MODE --"))
            self.stdout.write("Fetcher and parser will be called, but no data will be saved.")

            try:
                # Manually call fetcher and parser to simulate the process
                fetcher = TecnomegaDetailFetcher()
                parser = TecnomegaDetailParser()
                if not product.code:
                    raise CommandError(f"Product with code {product_code} has no code to fetch.")
                html = fetcher.fetch_product_detail_html(product.code)
                parsed_data = parser.parse(html)
                self.stdout.write(self.style.SUCCESS("Parsed data:"))
                import json

                self.stdout.write(json.dumps(parsed_data, indent=2))

            except Exception as e:
                logger.exception(f"An error occurred during the dry run for product code {product_code}.")
                raise CommandError(f"Dry run failed: {e}")
        else:
            self.stdout.write(self.style.NOTICE("Executing sync..."))
            success = orchestrator.sync_details(product, session_id="manual_sync")

            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully synced details for product: {product.code}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to sync details for product: {product.code}"))
