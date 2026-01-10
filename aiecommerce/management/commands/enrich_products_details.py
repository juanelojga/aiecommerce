import logging

from django.core.management.base import BaseCommand

from aiecommerce.services.tecnomega_product_details_fetcher_impl import (
    TecnomegaDetailFetcher,
    TecnomegaDetailParser,
)
from aiecommerce.services.tecnomega_product_details_fetcher_impl.orchestrator import (
    TecnomegaDetailOrchestrator,
)
from aiecommerce.services.tecnomega_product_details_fetcher_impl.selector import TecnomegaDetailSelector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to execute the TecnomegaDetailOrchestrator for a single product.
    """

    help = "Fetches and syncs detailed product information from Tecnomega"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reprocess products that already have specs")
        parser.add_argument("--dry-run", action="store_true", help="Perform API calls without saving to DB")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between products")

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        # Initialize the specific specification service and its orchestrator
        selector = TecnomegaDetailSelector()
        fetcher = TecnomegaDetailFetcher()
        parser = TecnomegaDetailParser()

        orchestrator = TecnomegaDetailOrchestrator(selector=selector, fetcher=fetcher, parser=parser)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
