from django.core.management.base import BaseCommand

from aiecommerce.services.enrichment_images_impl.orchestrator import EnrichmentImagesOrchestrator
from aiecommerce.services.enrichment_images_impl.selector import EnrichmentImagesCandidateSelector


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
        selector = EnrichmentImagesCandidateSelector()
        orchestrator = EnrichmentImagesOrchestrator(selector)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        if stats["total"] == 0:
            self.stdout.write(self.style.WARNING("No products found without images."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
            self.stdout.write(self.style.SUCCESS(f"Enqueued {stats['processed']}/{stats['total']} tasks"))
