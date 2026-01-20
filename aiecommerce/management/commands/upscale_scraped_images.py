from django.core.management.base import BaseCommand

from aiecommerce.services.upscale_images_impl.orchestrator import UpscaleHighResOrchestrator
from aiecommerce.services.upscale_images_impl.selector import UpscaleHighResSelector


class Command(BaseCommand):
    help = "Enqueues tasks to upscale images for products."

    def add_arguments(self, parser):
        parser.add_argument("--code", type=str, default=None, help="Process a single product identified by its code.")
        parser.add_argument("--dry-run", action="store_true", help="Show which products would be processed, but do not enqueue any tasks.")

    def handle(self, *args, **options):
        code = options["code"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        # Initialize the selector and the main orchestrator
        selector = UpscaleHighResSelector()
        orchestrator = UpscaleHighResOrchestrator(selector)

        # Run the upscale batch
        stats = orchestrator.run(product_code=code, dry_run=dry_run)

        if stats["total"] == 0:
            self.stdout.write(self.style.WARNING("No products found for image upscaling."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCompleted. Total candidates: {stats['processed']}"))
