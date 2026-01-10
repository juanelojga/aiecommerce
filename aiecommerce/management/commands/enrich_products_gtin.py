from django.conf import settings
from django.core.management.base import BaseCommand
from googleapiclient.discovery import build

from aiecommerce.services.gtin_search_impl.google_search_strategy import GoogleGTINStrategy
from aiecommerce.services.gtin_search_impl.orchestrator import GTINDiscoveryOrchestrator
from aiecommerce.services.gtin_search_impl.selector import GTINSearchSelector


class Command(BaseCommand):
    help = "Enqueues tasks to fetch and process images for products that do not have them."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reprocess products that already have specs")
        parser.add_argument("--dry-run", action="store_true", help="Show which products would be processed, but do not enqueue any tasks.")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between products")

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        # Initialize the selector and the main batch orchestrator
        selector = GTINSearchSelector()

        api_key = getattr(settings, "GOOGLE_API_KEY", None)
        search_engine_id = getattr(settings, "GOOGLE_SEARCH_ENGINE_ID", None)
        client = build("customsearch", "v1", developerKey=api_key) if api_key else None

        google_strategy = GoogleGTINStrategy(client, search_engine_id)
        orchestrator = GTINDiscoveryOrchestrator(selector, google_strategy)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        if stats["total"] == 0:
            self.stdout.write(self.style.WARNING("No products found without images."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
            self.stdout.write(self.style.SUCCESS(f"Enqueued {stats['processed']}/{stats['total']} tasks"))
